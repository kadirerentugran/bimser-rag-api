import asyncio
import asyncpg
import os

def get_raw_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")

async def analyze():
    # Setup paths and URL
    db_url = "postgresql://bimser:bimser_secret@localhost:5432/bimser_docs"
    docs_path = "/Users/erentugran/Desktop/kadirerentugran/bimser_docs/bimser_docs/app/data/docs"
    
    # 1. Check physical files
    all_files = []
    for root, _, files in os.walk(docs_path):
        for file in files:
            if file.endswith('.json'):
                rel_path = os.path.relpath(os.path.join(root, file), docs_path)
                all_files.append(rel_path)
                
    # 2. Check Database
    conn = await asyncpg.connect(db_url)
    
    db_docs = await conn.fetch("SELECT id, title, source_file FROM documents")
    db_files = [doc['source_file'] for doc in db_docs]
    
    emb_count = await conn.fetchval("SELECT count(*) FROM embeddings")
    
    print(f"--- FİZİKSEL DOSYALAR ({len(all_files)}) ---")
    for f in all_files:
        print(f" - {f}")
        
    print(f"\n--- VERİTABANI DOKÜMANLARI ({len(db_docs)}) ---")
    for d in db_docs:
        print(f" - {d['source_file']} (Başlık: {d['title']})")
        
    print(f"\n--- VEKTÖRLER ---")
    print(f"Toplam Vektör Sayısı: {emb_count}")
    
    # Analysis
    missing_in_db = set(all_files) - set(db_files)
    missing_on_disk = set(db_files) - set(all_files)
    
    print("\n--- ANALİZ ---")
    if missing_in_db:
        print("Fiziksel klasörde olan ancak veritabanında OLMAYAN dosyalar:")
        for m in missing_in_db:
            print(f" -> {m}")
    else:
        print("Veritabanı eksiksiz: Klasördeki tüm dosyalar db'de var (veya klasörde fazlalık yok).")
        
    if missing_on_disk:
        print("Veritabanında olan ancak fiziksel klasörden SİLİNMİŞ dosyalar:")
        for m in missing_on_disk:
            print(f" -> {m}")
    else:
        print("Disk eksiksiz: Veritabanındaki tüm dosyaların fiziksel karşılığı var.")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze())
