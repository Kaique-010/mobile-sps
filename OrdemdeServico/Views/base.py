from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
import logging

logger = logging.getLogger(__name__)

class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):
    """
    ViewSet base para suporte a múltiplos bancos de dados e verificação de módulo.
    Inclui suporte a transações e tratamento de erros padrão.
    """
    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error(f"Banco de dados não encontrado para {self.__class__.__name__}")
            raise NotFound("Banco de dados não encontrado.")
        return banco

    def get_queryset(self):
        return super().get_queryset().using(self.get_banco())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    @transaction.atomic(using='default')
    def create(self, request, *args, **kwargs):
        try:
            banco = self.get_banco()
            # Evita múltiplos acessos ao request.data
            data = getattr(request, '_cached_data', None)
            if data is None:
                data = request.data
                request._cached_data = data
            
            is_many = isinstance(data, list)
            serializer = self.get_serializer(data=data, many=is_many)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic(using=banco):
                self.perform_create(serializer)
                
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as ve:
            # Captura erros de validação
            logger.error(f"Erro de validação: {ve}")
            raise
        except Exception as e:
            logger.error(f"Erro ao processar requisição: {str(e)}")
            raise

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        try:
            banco = self.get_banco()
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic(using=banco):
                self.perform_update(serializer)
                
            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}

            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Erro ao atualizar: {str(e)}")
            raise

    def perform_update(self, serializer):
        serializer.save()
