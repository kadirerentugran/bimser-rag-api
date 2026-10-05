import logging

logger = logging.getLogger(__name__)

async def extract_and_understand_image(image_bytes: bytes) -> tuple[str, str]:
    """
    Demo Modu: Oracle ARM sunucusunda PaddleOCR 'Segmentation Fault' (Çekirdek Çökmesi)
    yarattığı için OCR özelliğini geçici olarak devre dışı bıraktık.
    Sadece Word içindeki resimleri es geçecek, yazıları başarıyla alacaktır.
    """
    logger.info("Demo modu: Resim (OCR) işleme atlandı.")
    return ("", "[Resim - OCR Analizi Devre Dışı]")
