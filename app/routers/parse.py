import datetime
from typing import Annotated
from fastapi import APIRouter, File, Form, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.auth import verify_api_key
from app.services.word_parser import parse_docx, save_as_json
from app.config import get_settings

router = APIRouter(prefix="/parse", tags=["Parse"])


@router.post("/word/preview")
async def preview_word(
    file: UploadFile = File(...),
    _: str = Depends(verify_api_key),
):
  
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Sadece .docx dosyaları kabul edilir.")

    content = await file.read()
    sections = await parse_docx(content)

    return {
        "filename": file.filename,
        "section_count": len(sections),
        "sections": sections,
    }


from pydantic import BaseModel
from typing import List, Any
import json
from fastapi import BackgroundTasks
import asyncpg

class SaveJsonRequest(BaseModel):
    title: str
    product: str
    parent: str
    description: str = ""
    sections: List[Any]

def get_raw_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")

@router.post("/save_json")
async def save_json(
    request: SaveJsonRequest,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key),
):
    """
    JSON verisini veritabanına kaydeder ve arka planda vektörlemeyi başlatır.
    """
    settings = get_settings()
    today = datetime.date.today().isoformat()
    
    payload = {
        "title": request.title,
        "parent": request.parent,
        "product": request.product,
        "description": request.description,
        "lastUpdated": today,
        "sections": request.sections,
    }
    
    from app.utils.slugify import slugify
    doc_slug = slugify(f"{request.product}-{request.parent}-{request.title}")
    
    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))
    try:
        doc_id = await conn.fetchval(
            """
            INSERT INTO documents (title, slug, product, parent, source_file, raw_json)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            ON CONFLICT (slug) DO UPDATE
              SET title=EXCLUDED.title, 
                  product=EXCLUDED.product, 
                  parent=EXCLUDED.parent,
                  raw_json=EXCLUDED.raw_json,
                  updated_at=now()
            RETURNING id
            """,
            request.title, doc_slug, request.product, request.parent, "", json.dumps(payload, ensure_ascii=False)
        )
    finally:
        await conn.close()
        
    # Trigger background task for embedding
    from app.routers.embeddings import embed_single_document
    background_tasks.add_task(embed_single_document, str(doc_id))

    return {
        "success": True,
        "saved_path": f"DB ID: {doc_id}",
        "section_count": len(request.sections),
    }
