import asyncio
from app.routers.embeddings import reindex
import httpx

async def main():
    try:
        await reindex(None)
    except httpx.HTTPStatusError as e:
        print("HTTP Status Error:", e)
        print("Response body:", e.response.text)
        print("Request body:", e.request.content.decode())

asyncio.run(main())
