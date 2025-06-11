from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from core.registry import get_licenca_db_config
from Entidades.models import Entidades 
from core.middleware import get_licenca_slug
from core.decorator import ModuloRequeridoMixin
from .models import Titulosreceber
from .serializers import TitulosreceberSerializer

class TitulosreceberViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modulo_requerido = 'Financeiro'
    serializer_class = TitulosreceberSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'titu_empr': ['exact'],
        'titu_clie': ['exact', 'icontains'],
        'titu_situ': ['exact'],
        'titu_venc': ['gte', 'lte'],
        'titu_aber': ['exact', 'icontains'],
    }
    search_fields = ['titu_titu' 'titu_clie', 'titu_aber']
    ordering_fields = ['titu_venc', 'titu_valo']
    ordering = ['titu_venc']

    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        queryset = Titulosreceber.objects.using(banco).all()

        cliente_nome = self.request.query_params.get('cliente_nome')
        empresa_id = self.request.query_params.get('titu_empr')

        if cliente_nome:
            ent_qs = Entidades.objects.using(banco).filter(enti_nome__icontains=cliente_nome)
            if empresa_id:
                ent_qs = ent_qs.filter(enti_empr=empresa_id)
            
            clientes_ids = list(ent_qs.values_list('enti_clie', flat=True))
            
            if clientes_ids:
                queryset = queryset.filter(titu_clie__in=clientes_ids)
            else:
                queryset = queryset.none()
        
        return queryset 


    def get_object(self):
        banco = get_licenca_db_config(self.request)
        return Titulosreceber.objects.using(banco).get(
            titu_empr=self.kwargs["titu_empr"],
            titu_fili=self.kwargs["titu_fili"],
            titu_clie=self.kwargs["titu_clie"],
            titu_titu=self.kwargs["titu_titu"],
            titu_seri=self.kwargs["titu_seri"],
            titu_parc=self.kwargs["titu_parc"],
        )
