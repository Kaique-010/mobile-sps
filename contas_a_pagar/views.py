from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Titulospagar
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from .serializers import TitulospagarSerializer

class TitulospagarViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'Financeiro'
    queryset = Titulospagar.objects.all()
    serializer_class = TitulospagarSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'titu_empr': ['exact'],
        'titu_forn': ['exact', 'icontains'],
        'titu_titu': ['exact'],
        'titu_venc': ['gte', 'lte'],
    }
    search_fields = ['titu_titu', 'titu_forn']
    ordering_fields = ['titu_venc', 'titu_valo']
    ordering = ['titu_venc']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

