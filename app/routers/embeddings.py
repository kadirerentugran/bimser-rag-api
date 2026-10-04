"""
embeddings.py router — Embedding pipeline endpoint'leri.

POST /embeddings/reindex  → Tüm JSON'ları vektörleştir
GET  /embeddings/status   → İndeksleme durumu
"""

import json
import time
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from app.auth import verify_api_key
from app.config import get_settings
from app.services.embedding_service import sections_to_chunks
from app.services.ollama_service import embed, health_check
from app.utils.slugify import slugify

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/embeddings", tags=["Embeddings"])

def get_raw_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")

@router.post("/reindex")
async def reindex(_: str = Depends(verify_api_key)):
    """
    Veritabanındaki (documents tablosu) tüm JSON dokümanlarını okuyup
    embedding'leri (vektörleri) baştan oluşturur.
    
    Strateji: Sadece embeddings tablosunu sil (DELETE) -> 
    Tüm dokümanları sırayla vektörleyip embeddings'e ekle.
    """
    settings = get_settings()
    start_time = time.time()
    
    ollama = await health_check()
    if not ollama["embed_ready"]:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding modeli hazır değil: {settings.ollama_embed_model}. "
                   f"'ollama pull {settings.ollama_embed_model}' komutunu çalıştırın.",
        )

    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))
    try:
        # Truncate embeddings table
        await conn.execute("DELETE FROM embeddings")

        records = await conn.fetch("SELECT id, title, product, parent, slug, source_file, raw_json FROM documents")
        
        if not records:
            return {"message": "İndekslenecek doküman bulunamadı.", "indexed_documents": 0}

        indexed = 0
        total_chunks = 0
        skipped = []

        for row in records:
            doc_id = row["id"]
            title = row["title"]
            product = row["product"] or ""
            parent = row["parent"] or ""
            rel_path = row["source_file"] or ""
            
            try:
                data = json.loads(row["raw_json"])
            except Exception as e:
                skipped.append({"id": str(doc_id), "reason": f"Geçersiz JSON: {e}"})
                continue

            sections = data.get("sections", [])
            
            # Docs sitesindeki URL href'i
            href = ""
            if rel_path:
                parts = rel_path.replace("\\", "/").replace(".json", "").split("/")
                href = "/docs/" + "/".join(slugify(p) for p in parts)
            else:
                href = f"/docs/{slugify(product)}/{slugify(parent)}/{slugify(title)}"

            doc_meta = {
                "title": title,
                "product": product,
                "parent": parent,
                "href": href,
            }

            chunks = sections_to_chunks(sections, doc_meta)

            batch = []
            for chunk in chunks:
                try:
                    vector = await embed(chunk["text"])
                    batch.append((
                        doc_id,
                        chunk["text"],
                        chunk["index"],
                        chunk["type"],
                        str(vector),
                        json.dumps(chunk["metadata"]),
                    ))
                except Exception as e:
                    logger.error(f"Chunk embedding hatası: {e}")

                if len(batch) >= 10:
                    await _insert_batch(conn, batch)
                    batch = []

            if batch:
                await _insert_batch(conn, batch)

            total_chunks += len(chunks)
            indexed += 1

    finally:
        await conn.close()

    duration = round(time.time() - start_time, 2)

    return {
        "success": True,
        "indexed_documents": indexed,
        "total_chunks": total_chunks,
        "duration_seconds": duration,
        "skipped": skipped,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def embed_single_document(doc_id):
    """
    Arka planda (BackgroundTasks) çağrılmak üzere tek bir dokümanı vektörler.
    doc_id string tipinde gelir, asyncpg UUID olarak parse eder.
    """
    settings = get_settings()
    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))
    try:
        # Clean existing embeddings for document
        await conn.execute("DELETE FROM embeddings WHERE document_id = $1::uuid", doc_id)
        
        row = await conn.fetchrow("SELECT title, product, parent, source_file, raw_json FROM documents WHERE id = $1::uuid", doc_id)
        if not row:
            return
            
        data = json.loads(row["raw_json"])
        title = row["title"]
        product = row["product"] or ""
        parent = row["parent"] or ""
        rel_path = row["source_file"] or ""
        sections = data.get("sections", [])
        
        href = ""
        if rel_path:
            parts = rel_path.replace("\\", "/").replace(".json", "").split("/")
            href = "/docs/" + "/".join(slugify(p) for p in parts)
        else:
            href = f"/docs/{slugify(product)}/{slugify(parent)}/{slugify(title)}"

        doc_meta = {
            "title": title,
            "product": product,
            "parent": parent,
            "href": href,
        }
        
        chunks = sections_to_chunks(sections, doc_meta)
        
        batch = []
        for chunk in chunks:
            try:
                vector = await embed(chunk["text"])
                batch.append((
                    doc_id,
                    chunk["text"],
                    chunk["index"],
                    chunk["type"],
                    str(vector),
                    json.dumps(chunk["metadata"]),
                ))
            except Exception as e:
                logger.error(f"Tekli doküman ({doc_id}) chunk embedding hatası: {e}")

            if len(batch) >= 10:
                await _insert_batch(conn, batch)
                batch = []

        if batch:
            await _insert_batch(conn, batch)
            
    except Exception as e:
        logger.error(f"Arka plan vektörleme hatası: {e}")
    finally:
        await conn.close()


async def _insert_batch(conn: asyncpg.Connection, batch: list):
    """Chunk listesini toplu olarak embeddings tablosuna ekler."""
    await conn.executemany(
        """
        INSERT INTO embeddings (document_id, chunk_text, chunk_index, chunk_type, embedding, metadata)
        VALUES ($1::uuid, $2, $3, $4, $5::vector, $6::jsonb)
        """,
        batch,
    )


@router.get("/status")
async def status(_: str = Depends(verify_api_key)):
    """Embedding durumunu ve Ollama sağlık bilgisini döner."""
    settings = get_settings()
    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))

    try:
        doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        emb_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
        last_doc = await conn.fetchval(
            "SELECT MAX(updated_at) FROM documents"
        )
    finally:
        await conn.close()

    ollama = await health_check()

    return {
        "document_count": doc_count,
        "embedding_count": emb_count,
        "last_reindex": last_doc.isoformat() if last_doc else None,
        "ollama": ollama,
        "db_status": "connected",
    }
