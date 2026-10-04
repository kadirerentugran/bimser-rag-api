import numpy as np
import cv2
from paddleocr import PaddleOCR

def test_ocr():
    ocr = PaddleOCR(use_angle_cls=True, lang='tr')
    # Create a dummy image with some text
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    cv2.putText(img, 'Test', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    result = ocr.ocr(img)
    print("RESULT TYPE:", type(result))
    if isinstance(result, list):
        print("RESULT LEN:", len(result))
        if len(result) > 0:
            print("FIRST ELEMENT TYPE:", type(result[0]))
            print("FIRST ELEMENT:", result[0])
    else:
        print("RESULT:", result)

if __name__ == "__main__":
    test_ocr()
