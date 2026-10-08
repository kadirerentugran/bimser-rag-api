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

SYSTEM_PROMPT = """Sen Bimser Çözüm ürünleri konusunda uzman, profesyonel bir teknik destek asistanısın.
Lütfen aşağıdaki kurallara KESİNLİKLE uy:
1. SOHBET/SELAMLAMA: Eğer kullanıcı "merhaba", "selam", "selamlar", "nasılsın", "günaydın" gibi günlük bir sohbet veya selamlama mesajı yazdıysa, AŞAĞIDAKİ BELGELERİ TAMAMEN GÖRMEZDEN GEL. Sadece kısa ve nazikçe kendini tanıt (örn: "Merhaba! Bimser Yapay Zeka Asistanıyım. Size dokümanlarımızla ilgili nasıl yardımcı olabilirim?"). Asla başka bir konudan bahsetme.
2. TEKNİK SORU: Eğer kullanıcı bir şey soruyorsa, SADECE sana verilen BELGELER kısmındaki bilgilere dayanarak yanıtla. 
3. BİLGİ YOKSA: Eğer sorunun cevabı sana verilen belgelerde geçmiyorsa, KESİNLİKLE kendi genel kültüründen veya internetten cevap uydurma. Sadece "Bu konuda belgelerimde yeterli bilgi bulamadım. Lütfen teknik destek ekibimizle iletişime geçin." de.
4. FORMAT: Cevabını doğrudan ver. "Kullanıcının sorusunu anlıyorum", "Belgelere göre cevap veriyorum" gibi gereksiz iç ses (monolog) cümleleri kurma. Sadece cevabı söyle.
"""

def get_raw_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")

class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000, description="Sorulacak soru")
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
    settings = get_settings()
    start_time = time.time()

    question_vector = await embed(body.question)

    conn = await asyncpg.connect(get_raw_db_url(settings.database_url))

    try:
        count = await conn.fetchval("SELECT count(*) FROM embeddings")
        if count == 0:
            raise HTTPException(
                status_code=503,
                detail="Henüz hiç doküman indekslenmemiş. Önce POST /embeddings/reindex endpoint'ini çalıştırın.",
            )

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
            answer="Seçtiğiniz filtreye ait hiçbir belge bulamadım.",
            sources=[],
            duration_ms=int((time.time() - start_time) * 1000),
            chunks_used=0,
        )

    # Threshold'u çok az arttırdık
    relevant_rows = [r for r in rows if r["similarity"] >= 0.35]

    context_parts = []
    for i, row in enumerate(relevant_rows, 1):
        meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
        source_title = meta.get("title", "Belge")
        context_parts.append(f"[{i}. Kaynak: {source_title}]\n{row['chunk_text']}")

    context = "\n\n---\n\n".join(context_parts) if context_parts else "Hiçbir belge bulunamadı."

    prompt = f"""{SYSTEM_PROMPT}

BELGELER:
{context}

KULLANICININ MESAJI/SORUSU: {body.question}

CEVAP:"""

    answer = await chat(prompt)

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
