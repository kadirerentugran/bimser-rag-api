"""
init_db.py — Tek seferlik veritabanı tablo kurulum scripti.

Çalıştırma:
  conda activate bimser-api
  cd /Users/erentugran/Desktop/kadirerentugran/bimser-api
  python scripts/init_db.py
"""

import asyncio
import asyncpg
import sys
import os

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

# asyncpg doğrudan URL (sqlalchemy prefix'i kaldır)
def get_raw_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


SQL = """
-- pgvector eklentisi
CREATE EXTENSION IF NOT EXISTS vector;

-- Dokümanlar tablosu
CREATE TABLE IF NOT EXISTS documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    product     TEXT,
    parent      TEXT,
    source_file TEXT,
    raw_json    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Embedding chunk'ları tablosu
CREATE TABLE IF NOT EXISTS embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text  TEXT NOT NULL,
    chunk_index INT  NOT NULL DEFAULT 0,
    chunk_type  TEXT NOT NULL DEFAULT 'text',
    embedding   VECTOR(768),
    metadata    JSONB DEFAULT '{}'::jsonb
);

-- HNSW indeksi (cosine similarity için)
CREATE INDEX IF NOT EXISTS embeddings_hnsw_idx
    ON embeddings USING hnsw (embedding vector_cosine_ops);

-- updated_at otomatik güncelleme trigger'ı
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS documents_updated_at ON documents;
CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
"""


async def init():
    settings = get_settings()
    raw_url = get_raw_db_url(settings.database_url)

    print("📡 PostgreSQL'e bağlanılıyor...")
    conn = await asyncpg.connect(raw_url)

    try:
        print("⚙️  Tablolar ve indeksler oluşturuluyor...")
        await conn.execute(SQL)
        print("✅ Tablolar başarıyla oluşturuldu.")
        print()
        print("Oluşturulan yapılar:")
        print("  📋 EXTENSION: vector (pgvector)")
        print("  📋 TABLE: documents")
        print("  📋 TABLE: embeddings")
        print("  📋 INDEX: embeddings_hnsw_idx (HNSW cosine)")
        print("  📋 TRIGGER: documents_updated_at")
    except Exception as e:
        print(f"❌ Hata: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init())
