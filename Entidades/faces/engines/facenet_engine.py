try:
    import cv2
    import numpy as np
    from deepface import DeepFace
except ImportError:
    cv2 = None
    np = None
    DeepFace = None

class FacesEngine:
    model_name = 'Facenet'
    
    def gerar_faces(self, img_rgb) -> list[float]:
        "Recebe a Imagem em BGR e RGB e retorna embedding Facenet 128"
        if cv2 is None or DeepFace is None:
            print("Bibliotecas de reconhecimento facial não disponíveis (cv2 ou deepface).")
            return None
        
        try:
            imagem_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)
            result = DeepFace.represent(imagem_rgb, model_name=self.model_name, enforce_detection=False, detector_backend='opencv')
            return result[0]['embedding']
        except Exception as e:
            print(f"Erro ao gerar embedding Facenet: {e}")
            return None

    def comparar_faces(self, face1, face2, threshold=10):
        """
        Compara dois embeddings e retorna True se forem da mesma pessoa.
        Face1 e Face2 são listas ou arrays numpy de floats (embeddings).
        Threshold para Facenet (Euclidean L2) é geralmente ao redor de 10.
        """
        if face1 is None or face2 is None or np is None:
            return False
        
        # Converte para numpy array se necessário
        f1 = np.array(face1)
        f2 = np.array(face2)
        
        # Distância Euclidiana
        dist = np.linalg.norm(f1 - f2)
        
        return dist < threshold