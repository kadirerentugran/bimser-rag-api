from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from app.auth import verify_api_key
from app.services.document_service import list_all_documents, get_document, save_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/")
async def list_documents(_: str = Depends(verify_api_key)):
    """Tüm JSON dokümanlarını listeler."""
    return list_all_documents()


@router.get("/{rel_path:path}")
async def get_doc(rel_path: str, _: str = Depends(verify_api_key)):
    """Belirli bir dokümanı döner."""
    doc = get_document(rel_path)
    if doc is None:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı.")
    return doc


class SaveDocumentRequest(BaseModel):
    rel_path: str
    data: dict[str, Any]


@router.put("/")
async def update_doc(
    body: SaveDocumentRequest,
    _: str = Depends(verify_api_key),
):
    """Bir dokümanı günceller (üzerine yazar)."""
    saved = save_document(body.rel_path, body.data)
    return {"success": True, "saved_path": saved}
