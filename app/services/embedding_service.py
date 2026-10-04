"""
embedding_service.py — JSON sections[] → chunk listesi dönüştürücü.

Her chunk: {text, type, index} formatında.
Chunk'lar daha sonra Ollama'ya gönderilip vektörleştirilir.
"""

from typing import Any


MAX_CHUNK_CHARS = 800    
OVERLAP_CHARS = 100     


def sections_to_chunks(sections: list[dict[str, Any]], doc_meta: dict) -> list[dict]:
    """
    sections[] dizisini embedding için hazır chunk listesine dönüştürür.

    doc_meta örneği:
      { "title": "...", "product": "...", "parent": "...", "href": "..." }
    """
    chunks = []
    i = 0

    while i < len(sections):
        section = sections[i]
        stype = section.get("type", "text")

        if stype == "heading":
            heading_text = section.get("content", "").strip()
            combined = heading_text

            if i + 1 < len(sections) and sections[i + 1].get("type") in ("text", "warning"):
                next_section = sections[i + 1]
                next_text = next_section.get("content", "").strip()
                combined = f"{heading_text}\n{next_text}"
                i += 1  # Sonraki section'ı atla (birleştirildi)

            if combined:
                chunks.append({
                    "text": combined,
                    "type": "heading",
                    "index": len(chunks),
                    "metadata": {**doc_meta, "chunk_type": "heading"},
                })

        elif stype == "text":
            content = section.get("content", "").strip()
            if not content:
                i += 1
                continue

            sub_chunks = _split_text(content)
            for sub in sub_chunks:
                chunks.append({
                    "text": sub,
                    "type": "text",
                    "index": len(chunks),
                    "metadata": {**doc_meta, "chunk_type": "text"},
                })

        elif stype == "code":
            code = section.get("code", "").strip()
            lang = section.get("language", "")
            if code:
                text = f"```{lang}\n{code}\n```" if lang else code
                if len(text) > MAX_CHUNK_CHARS:
                    sub_chunks = _split_text(text)
                    for sub in sub_chunks:
                        chunks.append({
                            "text": sub,
                            "type": "code",
                            "index": len(chunks),
                            "metadata": {**doc_meta, "chunk_type": "code", "language": lang},
                        })
                else:
                    chunks.append({
                        "text": text,
                        "type": "code",
                        "index": len(chunks),
                        "metadata": {**doc_meta, "chunk_type": "code", "language": lang},
                    })

        # ── WARNING ──────────────────────────────────────────────
        elif stype == "warning":
            content = section.get("content", "").strip()
            if content:
                text = f"⚠️ {content}"
                if len(text) > MAX_CHUNK_CHARS:
                    sub_chunks = _split_text(text)
                    for sub in sub_chunks:
                        chunks.append({
                            "text": sub,
                            "type": "warning",
                            "index": len(chunks),
                            "metadata": {**doc_meta, "chunk_type": "warning"},
                        })
                else:
                    chunks.append({
                        "text": text,
                        "type": "warning",
                        "index": len(chunks),
                        "metadata": {**doc_meta, "chunk_type": "warning"},
                    })

        elif stype == "image":
            caption = section.get("caption", "").strip()
            alt = section.get("alt", "").strip()
            ocr_content = section.get("ocr_content", "").strip()
            semantic_desc = section.get("semantic_description", "").strip()
            
            # Generate rich text chunk for image
            text_parts = []
            if caption:
                text_parts.append(f"[Görsel] {caption}")
            if semantic_desc:
                text_parts.append(f"Görsel Açıklaması: {semantic_desc}")
            if ocr_content:
                text_parts.append(f"Görseldeki Yazılar (OCR):\n{ocr_content}")
                
            if text_parts:
                full_text = "\n\n".join(text_parts)
                if len(full_text) > MAX_CHUNK_CHARS:
                    sub_chunks = _split_text(full_text)
                    for sub in sub_chunks:
                        chunks.append({
                            "text": sub,
                            "type": "image",
                            "index": len(chunks),
                            "metadata": {**doc_meta, "chunk_type": "image", "alt": alt},
                        })
                else:
                    chunks.append({
                        "text": full_text,
                        "type": "image",
                        "index": len(chunks),
                        "metadata": {**doc_meta, "chunk_type": "image", "alt": alt},
                    })

        elif stype == "table":
            headers = section.get("headers", [])
            rows = section.get("rows", [])
            if headers:
                lines = [" | ".join(str(h) for h in headers)]
                lines.append("-" * len(lines[0]))
                for row in rows:
                    lines.append(" | ".join(str(c) for c in row))
                text = "\n".join(lines)
                
                if len(text) > MAX_CHUNK_CHARS:
                    sub_chunks = _split_text(text)
                    for sub in sub_chunks:
                        chunks.append({
                            "text": sub,
                            "type": "table",
                            "index": len(chunks),
                            "metadata": {**doc_meta, "chunk_type": "table"},
                        })
                else:
                    chunks.append({
                        "text": text,
                        "type": "table",
                        "index": len(chunks),
                        "metadata": {**doc_meta, "chunk_type": "table"},
                    })

        i += 1

    return chunks


def _split_text(text: str) -> list[str]:
    """
    Uzun metni MAX_CHUNK_CHARS ile OVERLAP_CHARS örtüşmeli böler.
    """
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    parts = []
    start = 0
    while start < len(text):
        end = start + MAX_CHUNK_CHARS
        part = text[start:end]

        # Prevent mid-word splitting by slicing at last space
        if end < len(text):
            last_space = part.rfind(" ")
            if last_space > MAX_CHUNK_CHARS // 2:
                part = part[:last_space]
                end = start + last_space

        parts.append(part.strip())
        start = end - OVERLAP_CHARS  # Overlap: bağlamı koru

    return [p for p in parts if p]
