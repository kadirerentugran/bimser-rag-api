"""
ollama_service.py — Ollama API ile iletişim servisi.

İki temel fonksiyon:
  - embed(text)  → 768 boyutlu float listesi (nomic-embed-text:latest)
  - chat(prompt) → Türkçe metin cevabı (llama3.1:8b)
"""

import httpx
from fastapi import HTTPException
from app.config import get_settings

settings = get_settings()

TIMEOUT = httpx.Timeout(120.0, connect=10.0)


async def embed(text: str) -> list[float]:
    """
    Verilen metni nomic-embed-text:latest ile 768 boyutlu vektöre çevirir.
    """
    url = f"{settings.ollama_base_url}/api/embeddings"
    payload = {
        "model": settings.ollama_embed_model,
        "prompt": text,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama servisine erişilemiyor: {settings.ollama_base_url}. "
                   "Ollama'nın çalıştığından emin olun ('ollama serve').",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Ollama embedding zaman aşımına uğradı. Metin çok uzun olabilir.",
        )
    except KeyError:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama geçersiz yanıt döndürdü. "
                   f"'{settings.ollama_embed_model}' modeli yüklü mü? "
                   f"'ollama pull {settings.ollama_embed_model}' komutunu deneyin.",
        )


async def chat(prompt: str) -> str:
    """
    Verilen prompt'u llama3.1:8b modeline gönderir, Türkçe cevap döner.
    """
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {
        "model": settings.ollama_llm_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,      # Düşük: tutarlı, az yaratıcı (teknik doküman için ideal)
            "top_p": 0.9,
            "num_predict": 1024,     # Maksimum cevap token sayısı
        },
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama servisine erişilemiyor: {settings.ollama_base_url}.",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Ollama LLM zaman aşımına uğradı. Model meşgul olabilir, tekrar deneyin.",
        )
    except KeyError:
        raise HTTPException(
            status_code=502,
            detail=f"'{settings.ollama_llm_model}' modeli bulunamadı. "
                   f"'ollama pull {settings.ollama_llm_model}' komutunu deneyin.",
        )


async def health_check() -> dict:
    """Ollama'nın çalışıp çalışmadığını ve modellerin mevcut olup olmadığını kontrol eder."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            return {
                "status": "online",
                "models": models,
                "llm_ready": any(settings.ollama_llm_model.split(":")[0] in m for m in models),
                "embed_ready": any(settings.ollama_embed_model.split(":")[0] in m for m in models),
            }
    except Exception:
        return {"status": "offline", "models": [], "llm_ready": False, "embed_ready": False}
