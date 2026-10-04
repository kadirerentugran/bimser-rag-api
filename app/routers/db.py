from fastapi import APIRouter, Depends, HTTPException
import asyncpg
import os

from app.auth import verify_api_key
from app.config import get_settings

router = APIRouter(prefix="/db", tags=["Database Management"])

def get_raw_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")

@router.get("/documents")
async def list_db_documents(_: str = Depends(verify_api_key)):
    """PostgreSQL 'documents' tablosundaki tüm dokümanları (JSON detayları hariç) listeler."""
    settings = get_settings()
    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))
    try:
        rows = await conn.fetch(
            """
            SELECT id, title, slug, product, parent, source_file, updated_at, created_at 
            FROM documents
            ORDER BY updated_at DESC
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@router.delete("/documents/{doc_id}")
async def delete_db_document(doc_id: str, _: str = Depends(verify_api_key)):
    """
    Seçili dokümanı PostgreSQL 'documents' tablosundan (ve ona bağlı vektörleri) siler.
    """
    settings = get_settings()
    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))
    try:
        # Find document by ID
        row = await conn.fetchrow("SELECT title FROM documents WHERE id = $1::uuid", doc_id)
        if not row:
            raise HTTPException(status_code=404, detail="Doküman veritabanında bulunamadı.")
            
        # Delete document (CASCADE drops associated embeddings)
        await conn.execute("DELETE FROM documents WHERE id = $1::uuid", doc_id)
            
        return {"success": True, "message": f"Doküman başarıyla silindi.", "deleted_file": row["title"]}
    finally:
        await conn.close()


from fastapi.responses import Response

@router.get("/documents/{doc_id}/download")
async def download_db_document(doc_id: str, _: str = Depends(verify_api_key)):
    """
    Belirli bir dokümanın JSON verisini indirir.
    """
    settings = get_settings()
    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))
    try:
        row = await conn.fetchrow("SELECT title, slug, raw_json FROM documents WHERE id = $1::uuid", doc_id)
        if not row:
            raise HTTPException(status_code=404, detail="Doküman veritabanında bulunamadı.")
            
        json_data = row["raw_json"]
        filename = f"{row['slug']}.json"
        
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    finally:
        await conn.close()

@router.get("/documents/by-slug/{slug}")
async def get_document_by_slug(slug: str):
    """
    Slug değerine göre dokümanı getirir (Örn: bimser_docs için).
    API key doğrulaması bilerek istenmiyor çünkü Next.js Server Component'ten veya clienttan okunacak (isteğe bağlı eklenebilir).
    """
    settings = get_settings()
    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))
    try:
        row = await conn.fetchrow("SELECT raw_json FROM documents WHERE slug = $1", slug)
        if not row:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı.")
            
        return Response(content=row["raw_json"], media_type="application/json")
    finally:
        await conn.close()
