import os
import json
import re
import io
from typing import Any
from docx import Document
from docx.oxml.ns import qn
import mammoth

from app.utils.slugify import slugify



def _cell_text(cell) -> str:
    return " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())



from app.services.ocr_service import extract_and_understand_image

async def parse_docx(file_bytes: bytes) -> list[dict[str, Any]]:
    """
    Bir .docx dosyasını sections[] dizisine dönüştürür.
    Desteklenen çıktı tipleri:
      - heading (level 2 veya 3)
      - text
      - code
      - table
      - image (PaddleOCR ile metin ve anlamsal çıkarım)
      - warning (ünlemli paragraflar)
    """
    doc = Document(io.BytesIO(file_bytes))
    sections: list[dict[str, Any]] = []

    image_counter = 0

    for block in doc.element.body:
        tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag

        if tag == "p":
            para = None
            # python-docx Paragraph nesnesini bul
            from docx.text.paragraph import Paragraph
            para = Paragraph(block, doc)

            text = para.text.strip()

            # Image Block Detection
            blips = block.findall(".//" + qn("a:blip"))
            if blips:
                image_counter += 1
                ocr_text = ""
                semantic_desc = ""
                
                # Resim baytlarını çıkar
                embed_id = blips[0].get(qn("r:embed"))
                if embed_id and embed_id in doc.part.related_parts:
                    img_part = doc.part.related_parts[embed_id]
                    image_bytes = img_part.blob
                    
                    # OCR and Semantic Analysis
                    ocr_text, semantic_desc = await extract_and_understand_image(image_bytes)

                sections.append({
                    "type": "image",
                    "src": f"/images/placeholder_{image_counter}.png",
                    "alt": f"Görsel {image_counter}",
                    "caption": f"OCR Çıktısı: {semantic_desc}",
                    "ocr_content": ocr_text,
                    "semantic_description": semantic_desc
                })
                continue # resim varsa p tag'ini bitir
            
            if not text:
                continue

            style_name = para.style.name if para.style else ""

            if style_name.startswith("Heading 1") or re.match(r"^#{1}\s", text):
                sections.append({"type": "heading", "level": 2, "content": text.lstrip("# ").strip()})

            elif style_name.startswith("Heading 2") or re.match(r"^#{2}\s", text):
                sections.append({"type": "heading", "level": 3, "content": text.lstrip("# ").strip()})

            elif style_name.startswith("Heading 3") or re.match(r"^#{3}\s", text):
                sections.append({"type": "heading", "level": 4, "content": text.lstrip("# ").strip()})

            elif "Code" in style_name:
                if sections and sections[-1].get("type") == "code":
                    sections[-1]["code"] += "\n" + text
                else:
                    sections.append({"type": "code", "language": "bash", "code": text})

            elif text.startswith(("⚠", "Not:", "Dikkat:", "UYARI:", "WARNING:")):
                sections.append({"type": "warning", "content": text})

            else:
                sections.append({"type": "text", "content": text})

        elif tag == "tbl":
            from docx.table import Table
            table = Table(block, doc)

            rows = table.rows
            if not rows:
                continue

            headers = [_cell_text(cell) for cell in rows[0].cells]
            data_rows = [
                [_cell_text(cell) for cell in row.cells]
                for row in rows[1:]
            ]

            sections.append({
                "type": "table",
                "headers": headers,
                "rows": data_rows
            })

    return sections

def save_as_json(
    sections: list[dict],
    title: str,
    product: str,
    parent: str,
    description: str,
    docs_data_path: str,
    last_updated: str,
) -> str:
    """
    sections[] verisini standart Headless CMS şemasına göre
    docs_data_path içine kaydeder. Dosya yolu döner.
    """
    product_slug = slugify(product)
    parent_slug = slugify(parent)
    title_slug = slugify(title)

    # Klasör yolu
    folder = os.path.join(docs_data_path, product_slug, parent_slug)
    os.makedirs(folder, exist_ok=True)

    # Dosya yolu
    file_path = os.path.join(folder, f"{title_slug}.json")

    payload = {
        "title": title,
        "parent": parent,
        "product": product,
        "description": description,
        "lastUpdated": last_updated,
        "sections": sections,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return file_path
