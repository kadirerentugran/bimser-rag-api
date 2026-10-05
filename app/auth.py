from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    # Mülakat demosu için güvenlik duvarını geçici olarak devre dışı bıraktık
    return "dummy_key"
