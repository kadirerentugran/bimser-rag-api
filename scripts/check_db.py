import asyncio
import asyncpg
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

async def main():
    settings = get_settings()
    raw_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(raw_url)
    
    docs = await conn.fetchval("SELECT count(*) FROM documents")
    embs = await conn.fetchval("SELECT count(*) FROM embeddings")
    
    print(f"Documents: {docs}")
    print(f"Embeddings: {embs}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
