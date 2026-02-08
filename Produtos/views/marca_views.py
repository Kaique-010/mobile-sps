from rest_framework.generics import ListAPIView
from rest_framework.filters import SearchFilter
from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from ..serializers.marca_serializer import MarcaSerializer
from ..consultas.marca_consultas import listar_marcas

class MarcaListView(ModuloRequeridoMixin, ListAPIView):
    modulo_necessario = 'Produtos'
    serializer_class = MarcaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return listar_marcas(banco)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
