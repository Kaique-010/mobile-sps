# views.py
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import ListaCasamento
from .serializers import ListaCasamentoSerializer

class ListaCasamentoViewSet(viewsets.ModelViewSet):

    queryset = ListaCasamento.objects.all().order_by('list_nume')
    serializer_class = ListaCasamentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['list_clie__nome', 'list_nume']

class ItensListaCasamentoViewSet(viewsets.ModelViewSet):
    queryset = ItensListaCasamento.objects.all()
    serializer_class = ItensListaCasamentoSerializer