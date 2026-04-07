from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
import logging
from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.cache_service import build_cache_key, cache_get_or_set
from ..models import UnidadeMedida
from ..serializers.unidade_medida_serializer import UnidadeMedidaSerializer

logger = logging.getLogger(__name__)


class UnidadeMedidaListView(ModuloRequeridoMixin, ListAPIView):
    modulo_necessario = 'Produtos'
    serializer_class = UnidadeMedidaSerializer
    
    def get(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
            
        banco = get_licenca_db_config(self.request)
        
        if banco:
            cache_key = build_cache_key("produtos", banco, "unidades_medida")
            queryset, _ = cache_get_or_set(
                key=cache_key,
                timeout=600,
                factory=lambda: list(UnidadeMedida.objects.using(banco).all().order_by('unid_desc')),
                logger_instance=logger,
            )
            serializer = UnidadeMedidaSerializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response([])
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
