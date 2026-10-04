import asyncio
from app.routers.embeddings import reindex
from app.config import get_settings

async def main():
    try:
        # Simulate hitting the endpoint
        result = await reindex(None)
        print("Success:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
