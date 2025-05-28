from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from core.decorator import ModuloRequeridoMixin
from .models import Titulosreceber
from .serializers import TitulosreceberSerializer



class TitulosreceberViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modulo_requerido = 'Financeiro'
    queryset = Titulosreceber.objects.all()
    serializer_class = TitulosreceberSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'titu_empr': ['exact'],
        'titu_clie': ['exact', 'icontains'],
        'titu_situ': ['exact'],
        'titu_venc': ['gte', 'lte'],
    }
    search_fields = ['titu_titu' 'titu_clie']
    ordering_fields = ['titu_venc', 'titu_valo']
    ordering = ['titu_venc']
