import base64
import numpy as np
import cv2

def base64_to_img(base64_string):
    """
    Converte uma string base64 para uma imagem OpenCV (numpy array).
    Retorna None se falhar.
    """
    try:
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
        
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None