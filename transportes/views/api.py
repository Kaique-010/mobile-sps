from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.utils import get_licenca_db_config
from transportes.models import Cte
from transportes.serializers.emissao import CteEmissaoSerializer
from transportes.serializers.tipo import CteTipoSerializer
from transportes.serializers.rota import CteRotaSerializer
from transportes.serializers.seguro import CteSeguroSerializer
from transportes.serializers.carga import CteCargaSerializer
from transportes.serializers.tributacao import CteTributacaoSerializer
from transportes.serializers.completo import CteCompletoSerializer


import logging

logger = logging.getLogger(__name__)

class CteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento completo de CT-e.
    Suporta atualização parcial por abas e ações de emissão.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero', 'chave_acesso', 'destinatario__nome', 'remetente__nome']
    ordering_fields = ['id', 'numero', 'emissao', 'status']
    ordering = ['-id']

    def get_queryset(self):
        slug = get_licenca_db_config(self.request)
        return Cte.objects.using(slug).all()

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return CteCompletoSerializer
        elif self.action == 'create':
            return CteEmissaoSerializer # Criação básica
        elif self.action == 'partial_update':
            # Se for patch genérico, usa completo ou emissão básica
            return CteEmissaoSerializer
        return CteCompletoSerializer

    def perform_create(self, serializer):
        slug = get_licenca_db_config(self.request)
        # Usa o serializer para validar, mas o service para criar se necessário
        # Ou simplesmente salva com o serializer e ajusta status
        serializer.save(status='RAS')

    @action(detail=True, methods=['patch'], url_path='aba-emissao')
    def aba_emissao(self, request, pk=None):
        instance = self.get_object()
        serializer = CteEmissaoSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='aba-tipo')
    def aba_tipo(self, request, pk=None):
        instance = self.get_object()
        serializer = CteTipoSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='aba-rota')
    def aba_rota(self, request, pk=None):
        instance = self.get_object()
        serializer = CteRotaSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='aba-seguro')
    def aba_seguro(self, request, pk=None):
        instance = self.get_object()
        serializer = CteSeguroSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='aba-carga')
    def aba_carga(self, request, pk=None):
        instance = self.get_object()
        serializer = CteCargaSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='aba-tributacao')
    def aba_tributacao(self, request, pk=None):
        instance = self.get_object()
        serializer = CteTributacaoSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='emitir')
    def emitir(self, request, pk=None):
        slug = get_licenca_db_config(request)
        cte = self.get_object()
        
        try:
            # Em API REST, geralmente chamamos o service diretamente e retornamos
            # o status atualizado, ou o ID da task se for assíncrono.
            # Vamos chamar a task para manter consistência com o web.
            from transportes.tasks.emitir_cte import emitir_cte_task
            task = emitir_cte_task.delay(cte.id, slug)
            
            return Response({
                "status": "processando",
                "task_id": task.id,
                "message": "Emissão de CT-e iniciada."
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Erro ao emitir CTe via API: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='consultar-recibo')
    def consultar_recibo(self, request, pk=None):
        slug = get_licenca_db_config(request)
        cte = self.get_object()
        
        if not cte.recibo:
             return Response({"error": "CT-e não possui recibo."}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            from transportes.tasks.consultar_recibo import consultar_recibo_task
            task = consultar_recibo_task.delay(cte.id, cte.recibo, slug)
            
            return Response({
                "status": "processando",
                "task_id": task.id,
                "message": "Consulta iniciada."
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
