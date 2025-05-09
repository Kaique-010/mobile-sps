from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from django.db import transaction, IntegrityError
from rest_framework.decorators import api_view
from .models import SaidasEstoque
from .serializers import SaidasEstoqueSerializer
import logging
logger = logging.getLogger(__name__)


class SaidasEstoqueViewSet(ModelViewSet):
    serializer_class = SaidasEstoqueSerializer
    filter_backends = [SearchFilter]
    search_fields = ['said_enti', 'said_prod']

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', 'default')
        return SaidasEstoque.objects.using(db_alias).all().order_by('-said_sequ')

    def create(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias', 'default')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic(using=db_alias):
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            logger.error(f"IntegrityError: {e}")
            raise ValidationError({"detail": "Erro de integridade no banco de dados."})
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info(f"🗑️ [VIEW DELETE] Solicitada exclusão do ID {instance.said_sequ}")
        try:
            self.perform_destroy(instance.using(getattr(request, 'db_alias', 'default')))
            logger.info(f"🗑️ [VIEW DELETE] Exclusão do ID {instance.said_sequ} concluída")
            logger.info(f"✅ Exclusão concluída: ID {instance.said_sequ}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"❌ Falha ao excluir entrada: {e}")
            return Response({'erro': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
