from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from Pedidos import serializers
import Produtos
from rest_framework import status
from Produtos.serializers import ProdutoSerializer
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from .models import Entidades
from .serializers import EntidadesSerializer
from .utils import buscar_endereco_por_cep

class EntidadesViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modulo_requerido = 'Entidades'
    permission_classes = [IsAuthenticated]
    serializer_class = EntidadesSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['enti_nome', 'enti_nume']
    lookup_field = 'enti_clie'
    filterset_fields = ['enti_empr']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        print(f"\n🔍 Banco de dados selecionado: {banco}")
        
        if banco:
            return Entidades.objects.using(banco).all().order_by('enti_nome')
        return Entidades.objects.none()

    def get_serializer_class(self):
        return EntidadesSerializer
    
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    @action(detail=False, methods=['get'], url_path='buscar-endereco')
    @modulo_necessario('Entidades')
    def buscar_endereco(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        cep = request.GET.get('cep')
        if not cep:
            return Response({"erro": "CEP não informado"}, status=400)

        endereco = buscar_endereco_por_cep(cep)
        if endereco:
            return Response(endereco)
        else:
            return Response({"erro": "CEP inválido ou não encontrado"}, status=404)




