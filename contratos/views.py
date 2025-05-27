from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Contratosvendas
from .serializers import ContratosvendasSerializer



class ContratosViewSet(viewsets.ModelViewSet):
    queryset = Contratosvendas.objects.all()
    serializer_class = ContratosvendasSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'cont_cont': ['exact'],
        'cont_clie': ['exact', 'icontains'],
        'cont_data': ['exact'],
        'cont_prod': ['exact', 'icontains'],
    }
    search_fields = ['cont_cont' 'cont_clie']
    ordering_fields = ['cont_cont', 'cont_data']
    ordering = ['cont_cont']
