from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from ..models import UnidadeMedida
from ..serializers.unidade_medida_serializer import UnidadeMedidaSerializer

class UnidadeMedidaListView(ModuloRequeridoMixin, ListAPIView):
    modulo_necessario = 'Produtos'
    serializer_class = UnidadeMedidaSerializer
    
    def get(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
            
        banco = get_licenca_db_config(self.request)
        
        if banco:
            # Cache para unidades de medida
            cache_key = f"unidades_medida_{banco}"
            queryset = cache.get(cache_key)
            
            if not queryset:
                queryset = list(UnidadeMedida.objects.using(banco).all().order_by('unid_desc'))
                cache.set(cache_key, queryset, 1800)  # Cache por 30 minutos
                
            serializer = UnidadeMedidaSerializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response([])
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
