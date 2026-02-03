from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.shortcuts import get_object_or_404

from core.registry import get_licenca_db_config
from ..serializers import FaceInputSerializer, EntidadesFacesSerializer
from ..engines.facenet_engine import FacesEngine
from ..utils.image import base64_to_img
from ...models import Entidades
from ..models import EntidadesFaces


class EntidadesFacesViewSet(ViewSet):
    serializer_class = EntidadesFacesSerializer
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return EntidadesFaces.objects.using(banco).all()
    
    def create(self, request, enti_clie=None):
        banco = get_licenca_db_config(request)
        
        serializer = FaceInputSerializer(data=request.data)
        if serializer.is_valid():
            image_base64 = serializer.validated_data['image']
            img_rgb = base64_to_img(image_base64)
            if img_rgb is None:
                return Response({'error': 'Imagem inválida'}, status=status.HTTP_400_BAD_REQUEST)
            
            faces_engine = FacesEngine()
            embedding = faces_engine.gerar_faces(img_rgb)
            if embedding is None:
                return Response({'error': 'Erro ao gerar embedding Facenet'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Busca a entidade no banco correto
            entidade = get_object_or_404(Entidades.objects.using(banco), pk=enti_clie)
            
            entidade_faces = EntidadesFaces(entidade=entidade, face_enti=embedding)
            entidade_faces.save(using=banco)
            
            return Response(EntidadesFacesSerializer(entidade_faces).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

class ReconhecimentoFacesViewSet(ViewSet):
    serializer_class = EntidadesFacesSerializer

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return EntidadesFaces.objects.using(banco).all()
    
    @action(detail=False, methods=['post'])
    def reconhecer(self, request):
        banco = get_licenca_db_config(request)
        
        serializer = FaceInputSerializer(data=request.data)
        if serializer.is_valid():
            image_base64 = serializer.validated_data['image']
            img_rgb = base64_to_img(image_base64)
            if img_rgb is None:
                return Response({'error': 'Imagem inválida'}, status=status.HTTP_400_BAD_REQUEST)
            
            faces_engine = FacesEngine()
            embedding = faces_engine.gerar_faces(img_rgb)
            if embedding is None:
                return Response({'error': 'Erro ao gerar embedding Facenet'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Comparar com as faces cadastradas no banco correto
            entidades_faces = EntidadesFaces.objects.using(banco).select_related('face_enti').all()
            
            # NOTA: Isso carrega todas as faces em memória. 
            # Para produção com muitos dados, idealmente usaríamos um banco vetorial ou busca otimizada.
            for entidade_faces in entidades_faces:
                if faces_engine.comparar_faces(embedding, entidade_faces.face_enti):
                    # Retornamos os dados da entidade encontrada
                    # Precisamos garantir que estamos acessando os dados corretamente
                    entidade = entidade_faces.face_enti # O nome do campo FK no model é face_enti
                    if faces_engine.comparar_faces(embedding, entidade_faces.face_embe):
                         # Serializa a entidade encontrada
                         # Aqui retornamos apenas o ID ou dados básicos para o frontend
                         return Response({
                             'entidade_id': entidade_faces.face_enti.pk,
                             'entidade_nome': entidade_faces.face_enti.enti_nome
                         }, status=status.HTTP_200_OK)

            return Response({'error': 'Nenhuma entidade encontrada'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)