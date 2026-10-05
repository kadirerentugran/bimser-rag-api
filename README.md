# Bimser RAG & Document Management API

Bu proje, şirket içi dokümanların (Word, PDF vb.) **Yapay Zeka (Ollama & Llama 3.1)** ve **Vektör Veritabanı (PostgreSQL + pgvector)** kullanılarak akıllı bir şekilde aranıp sorgulanmasını sağlayan RAG (Retrieval-Augmented Generation) altyapısının Backend kısmıdır.

## 🚀 Mimari ve Teknolojiler

*   **Backend:** Python 3.11, FastAPI
*   **Veritabanı:** PostgreSQL 16 + `pgvector` eklentisi
*   **Yapay Zeka (LLM):** Ollama (Llama 3.1 8B, Nomic-Embed-Text)
*   **OCR:** OpenCV, PaddleOCR (Opsiyonel)
*   **Konteynerleştirme:** Docker & Docker Compose

## 🛠️ Kurulum (Local Development)

Projeyi kendi bilgisayarınızda çalıştırmak için sisteminizde **Docker** ve **Docker Compose** kurulu olmalıdır.

1.  Projeyi klonlayın:
    ```bash
    git clone https://github.com/kadirerentugran/bimser-rag-api.git
    cd bimser-rag-api
    ```

2.  Sistemi Docker ile ayağa kaldırın:
    ```bash
    docker-compose up -d --build
    ```

3.  *Önemli:* Veritabanı tablolarını oluşturmak için bir kez şu komutu çalıştırın:
    ```bash
    docker exec -it bimser_api python scripts/init_db.py
    ```

Sistem ayağa kalktığında **Swagger API dökümantasyonuna** şu adresten ulaşabilirsiniz:
👉 `http://localhost:8000/docs`

## 🐳 Servisler

`docker-compose.yml` dosyası 3 temel servisi ayağa kaldırır:
*   `api`: FastAPI uygulaması (Port: 8000)
*   `db`: PostgreSQL vektör veritabanı (Port: 5432)
*   `ollama`: Yerel yapay zeka sunucusu (Port: 11434)
