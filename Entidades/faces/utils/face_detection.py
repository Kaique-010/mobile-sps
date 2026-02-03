import cv2

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def detect_and_crop(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5)

    if len(faces) != 1:
        raise ValueError("A imagem deve conter exatamente um rosto")

    x, y, w, h = faces[0]
    face = img[y:y+h, x:x+w]

    return cv2.resize(face, (160, 160))