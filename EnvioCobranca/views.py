from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from rest_framework.exceptions import ValidationError, NotFound
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
import logging

from .models import EnviarCobranca
from .serializers import EnviarCobrancaSerializer
from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin

logger = logging.getLogger(__name__)


class EnviarCobrancaViewSet(ReadOnlyModelViewSet, ModuloRequeridoMixin):
    serializer_class = EnviarCobrancaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ('empresa', 'filial', 'cliente_id', 'vencimento')
    search_fields = ('cliente_nome', 'numero_titulo')
    ordering_fields = ('vencimento', 'valor', 'cliente_nome')
    
    def get_object(self):
        """
        Obtém o objeto usando chave composta empresa/filial/cliente_id
        """
        try:
            # Priorizar parâmetros da URL
            empresa = self.kwargs.get('empresa')
            filial = self.kwargs.get('filial') 
            cliente_id = self.kwargs.get('cliente_id') or self.kwargs.get('cliente')
            
            # Fallback para query_params
            if not empresa:
                empresa = self.request.query_params.get('empresa')
            if not filial:
                filial = self.request.query_params.get('filial')
            if not cliente_id:
                cliente_id = self.request.query_params.get('cliente_id') or self.request.query_params.get('cliente')
                
            # Último recurso: request.data
            if not empresa and hasattr(self.request, 'data'):
                empresa = self.request.data.get('empresa')
            if not filial and hasattr(self.request, 'data'):
                filial = self.request.data.get('filial')
            if not cliente_id and hasattr(self.request, 'data'):
                cliente_id = self.request.data.get('cliente_id') or self.request.data.get('cliente')
            
            if not all([empresa, filial, cliente_id]):
                raise ValidationError("Empresa, filial e cliente_id são obrigatórios")
            
            slug = get_licenca_slug()
            if not slug:
                raise ValidationError("Slug da licença não encontrado")
            
            envio = get_object_or_404(
                EnviarCobranca.objects.using(slug),
                empresa=empresa,
                filial=filial,
                cliente_id=cliente_id
            )
            
            return envio
            
        except EnviarCobranca.DoesNotExist:
            raise NotFound("Envio de cobrança não encontrado")
        except Exception as e:
            logger.error(f"Erro ao buscar envio: {e}")
            raise ValidationError(f"Erro ao buscar envio: {str(e)}")
    
    def get_queryset(self):
        slug = get_licenca_slug()
        
        if not slug:
            return EnviarCobranca.objects.none()
        
        qs = EnviarCobranca.objects.using(slug).all()
    
        # Obter empresa e filial dos headers (prioridade) ou query params
        empresa = self.request.headers.get('X-Empresa') or self.request.query_params.get('empresa')
        filial = self.request.headers.get('X-Filial') or self.request.query_params.get('filial')
        cliente_id = self.request.query_params.get('cliente_id')
    
        # Aplicar filtros obrigatórios por empresa e filial
        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
    
        # Filtro de data por query string
        data_ini = self.request.query_params.get('data_ini')
        data_fim = self.request.query_params.get('data_fim')
        if data_ini and data_fim:
            qs = qs.filter(vencimento__range=[data_ini, data_fim])
    
        # Log para debug
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 ENVIO COBRANÇA - Empresa: {empresa}, Filial: {filial}, Registros: {qs.count()}")
    
        return qs

    