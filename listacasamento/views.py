# views.py
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import ListaCasamento, ItensListaCasamento
from rest_framework.decorators import action
from .serializers import ListaCasamentoSerializer, ItensListaCasamentoSerializer

class ListaCasamentoViewSet(viewsets.ModelViewSet):

    queryset = ListaCasamento.objects.all().order_by('list_nume')
    serializer_class = ListaCasamentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['list_clie__nome', 'list_nume']

class ItensListaCasamentoViewSet(viewsets.ModelViewSet):
    queryset = ItensListaCasamento.objects.all()
    serializer_class = ItensListaCasamentoSerializer
    def get_queryset(self):
        lista_id = self.request.query_params.get("lista")
        if lista_id:
            return ItensListaCasamento.objects.filter(lista=lista_id)
        return ItensListaCasamento.objects.all()

    @action(detail=False, methods=['post'])
    def adicionar_lote(self, request):
        """
        Espera:
        {
            "lista": 1,
            "itens": [
                {"produto": 5, "quantidade": 2},
                {"produto": 7, "quantidade": 1},
                ...
            ]
        }
        """
        lista_id = request.data.get("lista")
        itens = request.data.get("itens", [])

        criados = []
        for item in itens:
            criado = ItensListaCasamento.objects.create(
                lista_id=lista_id,
                produto_id=item["produto"],
                quantidade=item["quantidade"]
            )
            criados.append(criado)

        serializer = self.get_serializer(criados, many=True)
        return Response(serializer.data)