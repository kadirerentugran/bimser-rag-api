# Demo modunda olduğumuz için API Key korumasını tamamen kaldırdık.
# Fonksiyon ismini koruduk ki router'lardaki "Depends(verify_api_key)" patlamasın.

async def verify_api_key() -> str:
    return "demo_bypassed"

async def get_api_key() -> str:
    return "demo_bypassed"
