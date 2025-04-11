from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import Entidades
from .serializers import EntidadesSerializer
from .utils import buscar_endereco_por_cep

class EntidadesViewSet(viewsets.ModelViewSet):
    queryset = Entidades.objects.all().order_by('enti_nome')
    serializer_class = EntidadesSerializer
    filter_backends = [SearchFilter]
    search_fields = ['enti_nome', 'enti_nume']

    @action(detail=False, methods=['get'], url_path='buscar-endereco')
    def buscar_endereco(self, request):
        cep = request.GET.get('cep')
        if not cep:
            return Response({"erro": "CEP não informado"}, status=400)

        endereco = buscar_endereco_por_cep(cep)
        if endereco:
            return Response(endereco)
        else:
            return Response({"erro": "CEP inválido ou não encontrado"}, status=404)
