from rest_framework import viewsets
from .models import ImplantacaoTela
from .serializers import ImplantacaoTelaSerializer
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.rest_framework import FilterSet


class ImplantacaoTelaFilter(FilterSet):
    modulos = filters.CharFilter(field_name='modulos', lookup_expr='contains')
    telas = filters.CharFilter(field_name='telas', lookup_expr='contains')
    class Meta:
        model = ImplantacaoTela
        fields = ['modulos', 'telas']
        

class ImplantacaoTelaViewSet(viewsets.ModelViewSet):
    queryset = ImplantacaoTela.objects.all().order_by('-criado_em')
    serializer_class = ImplantacaoTelaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ImplantacaoTelaFilter
