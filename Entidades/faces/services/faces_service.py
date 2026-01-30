import numpy as np
from django.exceptions import ValidationError

from ..models import EntidadesFaces
from ..engines.facenet_engine import FacesEngine
from ..utils.deteccao import detectar_faces

max_embeddings = 5

def cosine_distance(a,b) -> float:
    "Recebe dois vetores e retorna a distância cosseno entre eles"
    return np.dot(a,b) / (np.linalg.norm(a) * np.linalg.norm(b))

class FacesService:
    def __init__(self):
        self.engine = FacesEngine()
    
    def registrar_face(self, entidade: Entidades, img_bgr: np.ndarray) -> None:
        "Recebe uma entidade e uma imagem em BGR e registra a face na entidade"
        face = detect_and_crop(img_bgr)
        if not face:
            raise ValidationError("Nenhuma face detectada na imagem")
        if len(faces) > max_embeddings:
            raise ValidationError(f"Máximo de {max_embeddings} faces permitidas")
        for face in faces:
            embedding = self.engine.gerar_faces(face)
            if not embedding:
                raise ValidationError("Erro ao gerar embedding Facenet")
            EntidadesFaces.objects.create(face_enti=entidade, embedding=embedding)

    def verificar_face(self, entidade: Entidades, img_bgr: np.ndarray) -> bool:
        "Recebe uma entidade e uma imagem em BGR e verifica se a face está registrada na entidade"
        faces = detectar_faces(img_bgr)
        if not faces:
            raise ValidationError("Nenhuma face detectada na imagem")
        if len(faces) > 1:
            raise ValidationError("Apenas uma face por imagem é permitida")
        face = faces[0]
        embedding = self.engine.gerar_faces(face)
        if not embedding:
            raise ValidationError("Erro ao gerar embedding Facenet")
        faces_registradas = EntidadesFaces.objects.filter(face_enti=entidade)
        if not faces_registradas:
            raise ValidationError("Nenhuma face registrada para esta entidade")
        for face_registrada in faces_registradas:
            dist = cosine_distance(embedding, face_registrada.embedding)
            if dist < 0.6:
                return True
        return False