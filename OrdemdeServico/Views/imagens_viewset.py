from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.db import transaction
from django.http import HttpResponse

from .base import BaseMultiDBModelViewSet
from ..models import Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois
from ..serializers import ImagemAntesSerializer, ImagemDuranteSerializer, ImagemDepoisSerializer
from ..utils import get_next_image_id

class FotosViewSet(BaseMultiDBModelViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=["get"], url_path="imagens/(?P<etapa>antes|durante|depois)/(?P<image_id>\\d+)")
    def imagem_bin(self, request, etapa=None, image_id=None, slug=None):
        banco = self.get_banco()
        modelo = {
            "antes": Ordemservicoimgantes,
            "durante": Ordemservicoimgdurante,
            "depois": Ordemservicoimgdepois,
        }.get(etapa)
        campo = {
            "antes": "iman_imag",
            "durante": "imdu_imag",
            "depois": "imde_imag",
        }[etapa]
        obj = modelo.objects.using(banco).get(pk=image_id)
        img = getattr(obj, campo)
        return HttpResponse(img, content_type="image/jpeg")

class ImagemAntesViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = ImagemAntesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        banco = self.get_banco()
        iman_empr = self.request.query_params.get('iman_empr')
        iman_fili = self.request.query_params.get('iman_fili')
        iman_orde = self.request.query_params.get('iman_orde')
        
        queryset = Ordemservicoimgantes.objects.using(banco)
        
        if iman_empr:
            queryset = queryset.filter(iman_empr=iman_empr)
        if iman_fili:
            queryset = queryset.filter(iman_fili=iman_fili)
        if iman_orde:
            queryset = queryset.filter(iman_orde=iman_orde)
            
        return queryset.order_by('iman_id')
    
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()
        
        required_fields = ['iman_orde', 'iman_empr', 'iman_fili', 'imagem_upload']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {"error": f"Campo obrigatório '{field}' não fornecido"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        

        if not data.get('imagem_upload') or not data.get('imagem_upload').strip():
            return Response(
                {"error": "Imagem é obrigatória"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Gerar próximo ID se não fornecido
        if not data.get('iman_id'):
            data['iman_id'] = get_next_image_id(
                banco,
                data.get('iman_orde'),
                data.get('iman_empr'),
                data.get('iman_fili'),
                'antes'
            )
        
        # Gerar próximo código se não fornecido
        if not data.get('iman_codi'):
            data['iman_codi'] = get_next_image_id(
                banco,
                data.get('iman_orde'),
                data.get('iman_empr'),
                data.get('iman_fili'),
                'antes'
            )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='bin', permission_classes=[AllowAny])
    def bin(self, request, *args, **kwargs):
        banco = self.get_banco()
        obj = self.get_object()
        blob = getattr(obj, 'iman_imag', None)
        if not blob:
            return Response(status=404)
        head = bytes(blob)[:12]
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            mime = 'image/jpeg'
        elif len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
            mime = 'image/png'
        elif len(head) >= 12 and head[:4] == b'RIFF' and head[8:12] == b'WEBP':
            mime = 'image/webp'
        else:
            mime = 'application/octet-stream'
        return HttpResponse(blob, content_type=mime)

    @action(detail=False, methods=['get'], url_path=r'(?P<orde>\d+)/(?P<image_id>\d+)/bin', permission_classes=[AllowAny])
    def bin_por_ordem(self, request, orde=None, image_id=None, *args, **kwargs):
        banco = self.get_banco()
        obj = Ordemservicoimgantes.objects.using(banco).filter(iman_orde=int(orde or 0), iman_id=int(image_id or 0)).first()
        if not obj or not obj.iman_imag:
            return Response(status=404)
        blob = obj.iman_imag
        head = bytes(blob)[:12]
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            mime = 'image/jpeg'
        elif len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
            mime = 'image/png'
        elif len(head) >= 12 and head[:4] == b'RIFF' and head[8:12] == b'WEBP':
            mime = 'image/webp'
        else:
            mime = 'application/octet-stream'
        return HttpResponse(blob, content_type=mime)


class ImagemDuranteViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = ImagemDuranteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        banco = self.get_banco()
        imdu_empr = self.request.query_params.get('imdu_empr')
        imdu_fili = self.request.query_params.get('imdu_fili')
        imdu_orde = self.request.query_params.get('imdu_orde')
        
        queryset = Ordemservicoimgdurante.objects.using(banco)
        
        if imdu_empr:
            queryset = queryset.filter(imdu_empr=imdu_empr)
        if imdu_fili:
            queryset = queryset.filter(imdu_fili=imdu_fili)
        if imdu_orde:
            queryset = queryset.filter(imdu_orde=imdu_orde)
            
        return queryset.order_by('imdu_id')
    
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()
        
        # Validar apenas campos obrigatórios essenciais
        required_fields = ['imdu_orde', 'imdu_empr', 'imdu_fili']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {"error": f"Campo obrigatório '{field}' não fornecido"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validar se imagem_upload não está vazia
        if not data.get('imagem_upload'):
            return Response(
                {"error": "Campo 'imagem_upload' é obrigatório e não pode estar vazio"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Gerar próximo ID se não fornecido
        if not data.get('imdu_id'):
            data['imdu_id'] = get_next_image_id(
                banco,
                data.get('imdu_orde'),
                data.get('imdu_empr'),
                data.get('imdu_fili'),
                'durante'
            )
        
        # Gerar próximo código se não fornecido
        if not data.get('imdu_codi'):
            data['imdu_codi'] = get_next_image_id(
                banco,
                data.get('imdu_orde'),
                data.get('imdu_empr'),
                data.get('imdu_fili'),
                'durante'
            )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='bin', permission_classes=[AllowAny])
    def bin(self, request, *args, **kwargs):
        banco = self.get_banco()
        obj = self.get_object()
        blob = getattr(obj, 'imdu_imag', None)
        if not blob:
            return Response(status=404)
        head = bytes(blob)[:12]
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            mime = 'image/jpeg'
        elif len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
            mime = 'image/png'
        elif len(head) >= 12 and head[:4] == b'RIFF' and head[8:12] == b'WEBP':
            mime = 'image/webp'
        else:
            mime = 'application/octet-stream'
        return HttpResponse(blob, content_type=mime)

    @action(detail=False, methods=['get'], url_path=r'(?P<orde>\d+)/(?P<image_id>\d+)/bin', permission_classes=[AllowAny])
    def bin_por_ordem(self, request, orde=None, image_id=None, *args, **kwargs):
        banco = self.get_banco()
        obj = Ordemservicoimgdurante.objects.using(banco).filter(imdu_orde=int(orde or 0), imdu_id=int(image_id or 0)).first()
        if not obj or not obj.imdu_imag:
            return Response(status=404)
        blob = obj.imdu_imag
        head = bytes(blob)[:12]
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            mime = 'image/jpeg'
        elif len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
            mime = 'image/png'
        elif len(head) >= 12 and head[:4] == b'RIFF' and head[8:12] == b'WEBP':
            mime = 'image/webp'
        else:
            mime = 'application/octet-stream'
        return HttpResponse(blob, content_type=mime)


class ImagemDepoisViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = ImagemDepoisSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        banco = self.get_banco()
        imde_empr = self.request.query_params.get('imde_empr')
        imde_fili = self.request.query_params.get('imde_fili')
        imde_orde = self.request.query_params.get('imde_orde')
        
        queryset = Ordemservicoimgdepois.objects.using(banco)
        
        if imde_empr:
            queryset = queryset.filter(imde_empr=imde_empr)
        if imde_fili:
            queryset = queryset.filter(imde_fili=imde_fili)
        if imde_orde:
            queryset = queryset.filter(imde_orde=imde_orde)
            
        return queryset.order_by('imde_id')
    
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()
        
        # Validar apenas campos obrigatórios essenciais
        required_fields = ['imde_orde', 'imde_empr', 'imde_fili']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {"error": f"Campo obrigatório '{field}' não fornecido"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validar se imagem_upload não está vazia
        if not data.get('imagem_upload'):
            return Response(
                {"error": "Campo 'imagem_upload' é obrigatório e não pode estar vazio"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Gerar próximo ID se não fornecido
        if not data.get('imde_id'):
            data['imde_id'] = get_next_image_id(
                banco,
                data.get('imde_orde'),
                data.get('imde_empr'),
                data.get('imde_fili'),
                'depois'
            )
        
        # Gerar próximo código se não fornecido
        if not data.get('imde_codi'):
            data['imde_codi'] = get_next_image_id(
                banco,
                data.get('imde_orde'),
                data.get('imde_empr'),
                data.get('imde_fili'),
                'depois'
            )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='bin', permission_classes=[AllowAny])
    def bin(self, request, *args, **kwargs):
        banco = self.get_banco()
        obj = self.get_object()
        blob = getattr(obj, 'imde_imag', None)
        if not blob:
            return Response(status=404)
        head = bytes(blob)[:12]
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            mime = 'image/jpeg'
        elif len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
            mime = 'image/png'
        elif len(head) >= 12 and head[:4] == b'RIFF' and head[8:12] == b'WEBP':
            mime = 'image/webp'
        else:
            mime = 'application/octet-stream'
        return HttpResponse(blob, content_type=mime)

    @action(detail=False, methods=['get'], url_path=r'(?P<orde>\d+)/(?P<image_id>\d+)/bin', permission_classes=[AllowAny])
    def bin_por_ordem(self, request, orde=None, image_id=None, *args, **kwargs):
        banco = self.get_banco()
        obj = Ordemservicoimgdepois.objects.using(banco).filter(imde_orde=int(orde or 0), imde_id=int(image_id or 0)).first()
        if not obj or not obj.imde_imag:
            return Response(status=404)
        blob = obj.imde_imag
        head = bytes(blob)[:12]
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            mime = 'image/jpeg'
        elif len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
            mime = 'image/png'
        elif len(head) >= 12 and head[:4] == b'RIFF' and head[8:12] == b'WEBP':
            mime = 'image/webp'
        else:
            mime = 'application/octet-stream'
        return HttpResponse(blob, content_type=mime)
