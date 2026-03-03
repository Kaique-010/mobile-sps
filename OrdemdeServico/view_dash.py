# views/os.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import  OrdensEletro
from .serializers import OrdensEletroSerializer    
from .filters.os import OrdensEletroFilter
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin
from Entidades.Views.base_cliente import IsCliente

class OrdensEletroViewSet(ModuloRequeridoMixin, viewsets.ReadOnlyModelViewSet):
    modulo_necessario = 'ordemdeservico'
    permission_classes = [IsAuthenticated | IsCliente]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = OrdensEletroFilter
    search_fields = ['nome_cliente', 'setor_nome', 'nome_responsavel', 'ordem_de_servico', 'pedido_compra', 'nf_entrada']
    serializer_class = OrdensEletroSerializer

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        qs = OrdensEletro.objects.using(banco).all()
        
        # BLINDAGEM CONTRA DATAS CORROMPIDAS
        # 1. Deferir campos de data originais
        qs = qs.defer('data_abertura', 'data_fim', 'ultima_alteracao')
        
        # 2. Injetar versões seguras como TEXT via SQL puro
        qs = qs.extra(select={
            'safe_data_abertura': """
                CASE WHEN EXTRACT(YEAR FROM data_abertura) BETWEEN 2020 AND 2100 
                THEN data_abertura::text ELSE NULL END
            """,
            'safe_data_fim': """
                CASE WHEN data_fim IS NOT NULL AND EXTRACT(YEAR FROM data_fim) BETWEEN 2020 AND 2100 
                THEN data_fim::text ELSE NULL END
            """,
            'safe_ultima_alteracao': """
                CASE WHEN ultima_alteracao IS NOT NULL AND EXTRACT(YEAR FROM ultima_alteracao) BETWEEN 2020 AND 2100 
                THEN ultima_alteracao::text ELSE NULL END
            """
        })
        
        # 3. Ordenar pelo campo seguro
        return qs.order_by('-safe_data_abertura', '-ordem_de_servico')
        
