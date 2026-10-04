from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    #
    database_url: str = "postgresql+asyncpg://bimser:bimser_secret@localhost:5432/bimser_docs"

    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text:latest"

    # Docs sitesi data klasörü
    docs_data_path: str = "/Users/erentugran/Desktop/kadirerentugran/bimser_docs/bimser_docs/app/data/docs" 

    admin_api_key: str = "14531453"

    ocr_language: str = "tr"
    ocr_gpu: bool = False

    # CORS
    allowed_origins: str = "http://localhost:3001,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"


@lru_cache() 
def get_settings() -> Settings: 
    return Settings()   #Cache Kullanımı ile Settings nesnesi tek bir örnek olarak tutulur ve tekrar tekrar oluşturulmaz. Bu, performansı artırır ve gereksiz kaynak kullanımını önler. Bunu Araştır. Singleton Yapı  EREN! 
