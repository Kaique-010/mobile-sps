from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction, IntegrityError
from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from ..models import SaidasEstoque
from .serializers import SaidasEstoqueSerializer
import logging

logger = logging.getLogger(__name__)


class SaidasEstoqueViewSet(ModuloRequeridoMixin, ModelViewSet):
    modulo_necessario = 'Saidas_Estoque'
    permission_classes = [IsAuthenticated]
    serializer_class = SaidasEstoqueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['said_enti', 'said_prod']
    filterset_fields = ['said_empr', 'said_fili']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if banco:
            return SaidasEstoque.objects.using(banco).all().order_by('-said_sequ')
        else:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic(using=banco):
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            logger.error(f"IntegrityError: {e}")
            raise ValidationError({"detail": "Erro de integridade no banco de dados."})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info(f"🗑️ [VIEW DELETE] Solicitada exclusão do ID {instance.said_sequ}")
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
        try:
            with transaction.atomic(using=banco):
                instance.delete()
            logger.info(f"🗑️ [VIEW DELETE] Exclusão do ID {instance.said_sequ} concluída")
            logger.info(f"✅ Exclusão concluída: ID {instance.said_sequ}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"❌ Falha ao excluir saída: {e}")
            return Response({'erro': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)