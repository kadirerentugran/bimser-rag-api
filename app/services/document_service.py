from __future__ import annotations
import os
import json
from typing import Any
from app.utils.slugify import slugify
from app.config import get_settings


def list_all_documents() -> list[dict[str, Any]]:
    """
    docs_data_path altındaki tüm JSON dosyalarını listeler.
    """
    settings = get_settings()
    base = settings.docs_data_path
    results = []

    if not os.path.exists(base):
        return results

    for root, _, files in os.walk(base):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, base)

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append({
                    "file_path": rel_path,
                    "title": data.get("title", fname),
                    "product": data.get("product", ""),
                    "parent": data.get("parent", ""),
                    "lastUpdated": data.get("lastUpdated", ""),
                    "section_count": len(data.get("sections", [])),
                })
            except Exception:
                results.append({
                    "file_path": rel_path,
                    "title": fname,
                    "error": "JSON okunamadı",
                })

    return results


def get_document(rel_path: str) -> dict[str, Any] | None:
    """
    Belirli bir JSON dokümanını döner.
    """
    settings = get_settings()
    full_path = os.path.join(settings.docs_data_path, rel_path)

    if not os.path.exists(full_path):
        return None

    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_document(rel_path: str, data: dict[str, Any]) -> str:
    """
    Bir JSON dokümanını kaydeder (üzerine yazar).
    """
    settings = get_settings()
    full_path = os.path.join(settings.docs_data_path, rel_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return full_path
