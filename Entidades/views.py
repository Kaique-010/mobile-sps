# views.py
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import Entidades
from .serializers import EntidadesSerializer

class EntidadesViewSet(viewsets.ModelViewSet):
    queryset = Entidades.objects.all().order_by('enti_nome')
    serializer_class = EntidadesSerializer
    filter_backends = [SearchFilter]
    search_fields = ['enti_nome', 'enti_nume']
