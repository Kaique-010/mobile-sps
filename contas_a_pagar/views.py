from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Titulospagar
from Entidades.models import Entidades 
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from .serializers import TitulospagarSerializer

class TitulospagarViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'Financeiro'
    serializer_class = TitulospagarSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'titu_empr': ['exact'],
        'titu_forn': ['exact'],
        'titu_titu': ['exact'],
        'titu_venc': ['gte', 'lte'],
        'titu_aber': ['exact'],
    }
    search_fields = ['titu_titu', 'titu_aber']
    ordering_fields = ['titu_emis','titu_venc', 'titu_valo']
    ordering = ['-titu_emis']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        queryset = Titulospagar.objects.using(banco).all()

        fornecedor_nome = self.request.query_params.get('fornecedor_nome')
        empresa_id = self.request.query_params.get('titu_empr')

        if fornecedor_nome:
            ent_qs = Entidades.objects.using(banco).filter(enti_nome__icontains=fornecedor_nome)
            if empresa_id:
                ent_qs = ent_qs.filter(enti_empr=empresa_id)
            
            fornecedor_ids = list(ent_qs.values_list('enti_clie', flat=True))
            
            if fornecedor_ids:
                queryset = queryset.filter(titu_forn__in=fornecedor_ids)
            else:
                queryset = queryset.none()
        
        return queryset 


            

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        return Titulospagar.objects.using(banco).get(
            titu_empr=self.kwargs["titu_empr"],
            titu_fili=self.kwargs["titu_fili"],
            titu_forn=self.kwargs["titu_forn"],
            titu_titu=self.kwargs["titu_titu"],
            titu_seri=self.kwargs["titu_seri"],
            titu_parc=self.kwargs["titu_parc"],
        )
