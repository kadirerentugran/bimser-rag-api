import asyncio
import numpy as np
import cv2
import logging
from paddleocr import PaddleOCR
from app.services.ollama_service import chat

logger = logging.getLogger(__name__)

logger.info("PaddleOCR modeli başlatılıyor (Bu işlem server ayağa kalkarken bir kez yapılır)...")
try:
    _ocr_instance = PaddleOCR(use_angle_cls=True, lang='tr')
    logger.info("PaddleOCR modeli başarıyla yüklü!")
except Exception as e:
    logger.error(f"PaddleOCR yüklenirken hata: {e}")
    _ocr_instance = None

def get_ocr():
    return _ocr_instance

async def extract_and_understand_image(image_bytes: bytes) -> tuple[str, str]:
    """
    Görsel byte dizisini alır, PaddleOCR ile okur ve Llama'ya özetletir.
    Dönüş: (ocr_content, semantic_description)
    """
    try:
        ocr = get_ocr()
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("Görsel formatı okunamadı.")
            return ("", "Görsel formatı okunamadı.")

        logger.info("PaddleOCR ile metin çıkarımı başlıyor...")
        result = await asyncio.to_thread(ocr.ocr, img)
        logger.info("PaddleOCR metin çıkarımı tamamlandı.")
        
        if not result or len(result) == 0:
            return ("", "Görselde herhangi bir metin bulunamadı.")
            
        res_dict = result[0]
        if 'rec_texts' not in res_dict or not res_dict['rec_texts']:
            return ("", "Görselde herhangi bir metin bulunamadı.")
            
        texts = res_dict['rec_texts']
        polys = res_dict.get('rec_polys', [])
        
        extracted_texts = []
        for i in range(len(texts)):
            text = texts[i]
            if i < len(polys) and len(polys[i]) > 0:
                # polys[i][0] -> sol üst köşe [X, Y]
                x, y = int(polys[i][0][0]), int(polys[i][0][1])
                extracted_texts.append(f"[{x},{y}]: {text}")
            else:
                extracted_texts.append(f"{text}")
            
        full_ocr_text = "\n".join(extracted_texts)
        
        # Send to LLM for semantic contextualization
        prompt = f"""
Aşağıdaki satırlar bir yazılım arayüzünün ekran görüntüsünden Optik Karakter Tanıma (OCR) ile çıkarılmıştır. 
Her satırın başında köşeli parantez içinde o yazının ekrandaki X,Y koordinatları vardır (örn: [15,20]).
Lütfen bu yazılara bakarak bu ekranın ne işe yaradığını ve kullanıcının muhtemelen ne işlemi yaptığını 1-2 cümleyle, net ve Türkçe bir şekilde özetle.
Eğer anlamsız yazılar varsa en belirgin menü isimlerini veya butonları baz al.

OCR ÇIKTISI:
{full_ocr_text}
"""
        logger.info("Ollama (Llama 3.1) özetlemesi için istek atılıyor...")
        semantic_desc = await chat(prompt)
        logger.info("Ollama (Llama 3.1) özetlemesi tamamlandı.")
        
        return (full_ocr_text, semantic_desc.strip())

    except Exception as e:
        logger.error(f"OCR işlemi sırasında hata: {str(e)}")
        return ("", f"OCR Hatası: {str(e)}")
