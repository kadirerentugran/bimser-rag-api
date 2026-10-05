from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import parse, documents, embeddings, ask, db

settings = get_settings()

app = FastAPI(
    title="Bimser API",
    description="Bimser Dokümantasyon Sistemi — Admin & RAG Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(parse.router)
app.include_router(documents.router)
app.include_router(embeddings.router)
app.include_router(ask.router)
app.include_router(db.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "service": "bimser-api",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
