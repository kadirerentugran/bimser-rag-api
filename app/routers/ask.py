"""
ask.py router — RAG tabanlı soru-cevap endpoint'i.

POST /ask → Türkçe soru al, ilgili chunk'ları bul, LLM ile cevap üret.
"""

import time
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import asyncpg

from app.config import get_settings
from app.services.ollama_service import embed, chat

router = APIRouter(prefix="/ask", tags=["RAG"])

SYSTEM_PROMPT = """Sen Bimser Çözüm ürünleri konusunda uzman bir teknik destek asistanısın.
Sana verilen belge parçalarına dayanarak soruyu TÜRKÇE olarak yanıtla.
Kullanıcının sorusunda yazım hataları (typo) veya eksik harfler olabilir. Sorusunun gelişinden ne kastettiğini anlamaya çalış ve belgelerdeki en uygun bilgiyi kullanarak cevap ver.
Eğer kullanıcının ne demek istediğini anlıyorsan fakat cevap aşağıdaki belgelerde gerçekten yoksa, o zaman "Bu konuda belgelerimde yeterli bilgi bulamadım. Lütfen teknik destek ekibimizle iletişime geçin." de.
Kendi bilginden tahmin veya yorum üretme. Sadece belgelerdeki bilgileri kullan.
Cevabı net, adım adım ve anlaşılır bir şekilde yaz."""


def get_raw_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="Sorulacak soru")
    product_filter: Optional[str] = Field(None, description="Opsiyonel ürün filtresi (örn: 'eBAPlus')")
    top_k: int = Field(5, ge=1, le=20, description="Getirilecek chunk sayısı")


class Source(BaseModel):
    title: str
    product: str
    href: str
    excerpt: str
    similarity: float


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    duration_ms: int
    chunks_used: int


@router.post("/", response_model=AskResponse)
async def ask(body: AskRequest):
    """
    RAG tabanlı soru-cevap.
    1. Soruyu vektöre çevir
    2. pgvector'den en benzer chunk'ları bul
    3. Llama3.1:8b ile Türkçe cevap üret
    """
    settings = get_settings()
    start_time = time.time()

    # 1. Generate embedding for query
    question_vector = await embed(body.question)

    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))

    try:
        # Tabloda hiç veri var mı kontrol et
        count = await conn.fetchval("SELECT count(*) FROM embeddings")
        if count == 0:
            raise HTTPException(
                status_code=503,
                detail="Henüz hiç doküman indekslenmemiş. "
                       "Önce POST /embeddings/reindex endpoint'ini çalıştırın.",
            )

        # 2. Vector similarity search
        if body.product_filter:
            rows = await conn.fetch(
                """
                SELECT
                    chunk_text,
                    metadata,
                    1 - (embedding <=> $1::vector) AS similarity
                FROM embeddings
                WHERE metadata->>'product' ILIKE $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                str(question_vector),
                f"%{body.product_filter}%",
                body.top_k,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                    chunk_text,
                    metadata,
                    1 - (embedding <=> $1::vector) AS similarity
                FROM embeddings
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                str(question_vector),
                body.top_k,
            )
    finally:
        await conn.close()

    if not rows:
        return AskResponse(
            answer="Seçtiğiniz filtreye (ürüne) ait belgelerimde hiçbir bilgi bulamadım. Lütfen filtreyi kaldırarak tekrar deneyin.",
            sources=[],
            duration_ms=int((time.time() - start_time) * 1000),
            chunks_used=0,
        )

    relevant_rows = [r for r in rows if r["similarity"] >= 0.25]

    if not relevant_rows:
        return AskResponse(
            answer="Sorunuzu tam olarak anlayamadım veya bu konuda belgelerimde yeterli bilgi bulamadım. Lütfen sorunuzu kontrol edip teknik destek ekibimizle iletişime geçin.",
            sources=[],
            duration_ms=int((time.time() - start_time) * 1000),
            chunks_used=0,
        )

    context_parts = []
    for i, row in enumerate(relevant_rows, 1):
        meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
        source_title = meta.get("title", "Belge")
        context_parts.append(f"[{i}. Kaynak: {source_title}]\n{row['chunk_text']}")

    context = "\n\n---\n\n".join(context_parts)

    # 4. Construct LLM prompt
    prompt = f"""{SYSTEM_PROMPT}

BELGELER:
{context}

SORU: {body.question}

CEVAP:"""

    # 5. Generate response using LLM
    answer = await chat(prompt)

    # 6. Prepare unique sources
    seen_hrefs = set()
    sources = []
    for row in relevant_rows:
        meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
        href = meta.get("href", "")
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        sources.append(Source(
            title=meta.get("title", ""),
            product=meta.get("product", ""),
            href=href,
            excerpt=row["chunk_text"][:200] + "..." if len(row["chunk_text"]) > 200 else row["chunk_text"],
            similarity=round(float(row["similarity"]), 3),
        ))

    duration_ms = int((time.time() - start_time) * 1000)

    return AskResponse(
        answer=answer,
        sources=sources,
        duration_ms=duration_ms,
        chunks_used=len(relevant_rows),
    )
