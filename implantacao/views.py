from rest_framework import viewsets
from .models import ImplantacaoTela
from .serializers import ImplantacaoTelaSerializer
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.rest_framework import FilterSet


class ImplantacaoTelaFilter(FilterSet):
    class Meta:
        model = ImplantacaoTela
        fields = ['modulo', 'tela']
        

class ImplantacaoTelaViewSet(viewsets.ModelViewSet):
    queryset = ImplantacaoTela.objects.all().order_by('-criado_em')
    serializer_class = ImplantacaoTelaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ImplantacaoTelaFilter 