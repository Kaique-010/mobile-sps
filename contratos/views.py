from rest_framework import viewsets, filters
from rest_framework import viewsets, status
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from datetime import datetime
from django.db import transaction
from rest_framework.response import Response
from Entidades.models import Entidades
from core.registry import get_licenca_db_config
from rest_framework.permissions import IsAuthenticated
from .models import Contratosvendas
from core.decorator import ModuloRequeridoMixin
from .serializers import ContratosvendasSerializer



import logging
logger = logging.getLogger(__name__)
class ContratosViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'contratos'
    serializer_class = ContratosvendasSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['cont_cont', 'cont_clie']
    search_fields = ['cont_cont', 'cont_clie']
    ordering_fields = ['cont_cont', 'cont_data']
    ordering = ['-cont_data', '-cont_cont']
    lookup_field = 'cont_cont'

    def get_queryset(self):
        # Pega qual banco de dados usar (multi-empresa)
        banco = get_licenca_db_config(self.request)

        # Pega empresa e filial do header da requisição
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")

        # Pega parâmetro opcional de nome do cliente (filtro extra)
        cliente_nome = self.request.query_params.get('cliente_nome')

        if banco and empresa_id and filial_id:
            # Usamos uma data mínima só pra garantir que nunca vem dado vazio
            data_minima = datetime(1900, 1, 1)

            # Query inicial filtrando por empresa, filial e datas válidas
            queryset = Contratosvendas.objects.using(banco).filter(
                Q(cont_data__gte=data_minima) | Q(cont_venc__gte=data_minima),
                cont_empr=empresa_id,
                cont_fili=filial_id
            )

           
            if cliente_nome:
                clientes = Entidades.objects.using(banco).filter(
                    enti_empr=empresa_id,
                    enti_nome__icontains=cliente_nome
                ).values_list('enti_clie', flat=True)

                queryset = queryset.filter(cont_clie__in=clientes)

            # Aqui entra o ORDER BY como no select:
    
            queryset = queryset.order_by('-cont_data', '-cont_cont')
            print("retornoqueryset", queryset)

            return queryset

        # Se não tiver parâmetros básicos, retorna vazio
        return Contratosvendas.objects.none()


    
    def destroy(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        contrato = self.get_object()

       
        if Contratosvendas.objects.using(banco).filter(cont_prod=contrato.cont_prod).exists():
            return Response(
                {"detail": "Não é possível excluir Contrato, há Produtos associados."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic(using=banco):
            contrato.delete()
            logger.info(f"🗑️ Exclusão do contrato ID {contrato.cont_cont} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def get_serializer_class(self):
        return ContratosvendasSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Banco
        context['banco'] = get_licenca_db_config(self.request)
        # Empresa/Filial dos headers (usadas no create e validações)
        context['empresa_id'] = self.request.headers.get("X-Empresa")
        context['filial_id'] = self.request.headers.get("X-Filial")
        return context
