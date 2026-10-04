import asyncio
import numpy as np
import cv2
import logging

logging.basicConfig(level=logging.INFO)

# app.services.ocr_service'i import edince PaddleOCR global olarak yüklenecek
from app.services.ocr_service import extract_and_understand_image

async def main():
    print("Test başlıyor. Dummy görsel oluşturuluyor...")
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    cv2.putText(img, 'Bimser Test Ekrani', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # Numpy array'i byte'a çevir (image_bytes simülasyonu)
    is_success, buffer = cv2.imencode(".png", img)
    if not is_success:
        print("Görsel byte'a çevrilemedi!")
        return
        
    image_bytes = buffer.tobytes()
    
    print("OCR servisi çağrılıyor...")
    ocr_text, desc = await extract_and_understand_image(image_bytes)
    
    print("\n--- SONUÇ ---")
    print(f"OCR ÇIKTISI:\n{ocr_text}")
    print(f"SEMANTİK AÇIKLAMA:\n{desc}")
    print("Test başarıyla tamamlandı!")

if __name__ == "__main__":
    asyncio.run(main())
