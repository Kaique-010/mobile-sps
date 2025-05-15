from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from django.db import transaction, IntegrityError
from rest_framework.decorators import api_view
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from .models import EntradaEstoque
from .serializers import EntradasEstoqueSerializer



import logging

logger = logging.getLogger(__name__)


class EntradasEstoqueViewSet(ModuloRequeridoMixin, ModelViewSet):
    modulo_necessario = 'Entradas_Estoque'
    permission_classes = [IsAuthenticated]
    serializer_class = EntradasEstoqueSerializer
    filter_backends = [SearchFilter]
    search_fields = ['entr_enti', 'entr_prod']

    def get_queryset(self): 
        banco = get_licenca_db_config(self.request)
        
        if banco:
            return EntradaEstoque.objects.using(banco).all().order_by('-entr_sequ')
        else:           
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
        

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
        logger.info(f"🗑️ [VIEW DELETE] Solicitada exclusão do ID {instance.entr_sequ}")
        try:
            db_alias = getattr(request, 'db_alias', 'default')
            with transaction.atomic(using=db_alias):
                instance.delete()
            logger.info(f"🗑️ [VIEW DELETE] Exclusão do ID {instance.entr_sequ} concluída")
            logger.info(f"✅ Exclusão concluída: ID {instance.entr_sequ}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"❌ Falha ao excluir entrada: {e}")
            return Response({'erro': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
