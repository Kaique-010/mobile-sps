try:
    import cv2
except ImportError:
    cv2 = None

_face_cascade = None

def get_face_cascade():
    global _face_cascade
    if cv2 is None:
        return None
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    return _face_cascade

def detect_and_crop(img):
    if cv2 is None:
        raise ImportError("OpenCV não está disponível")
    
    face_cascade = get_face_cascade()
    if face_cascade is None:
        raise ImportError("Não foi possível carregar o classificador de faces")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5)

    if len(faces) != 1:
        raise ValueError("A imagem deve conter exatamente um rosto")

    x, y, w, h = faces[0]
    face = img[y:y+h, x:x+w]

    return cv2.resize(face, (160, 160))