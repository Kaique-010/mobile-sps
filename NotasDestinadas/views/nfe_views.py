from rest_framework import viewsets, permissions
from core.utils import get_licenca_db_config
from django.db.models import Q

from ..models import NotaFiscalEntrada
from ..serializers import NotaFiscalEntradaSerializer, NotaFiscalEntradaListSerializer
from ..services.entrada_nfe_service import EntradaNFeService
from Produtos.models import Produtos


class NotaFiscalEntradaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/<slug>/nfe/entradas/
    """
    queryset = NotaFiscalEntrada.objects.all().order_by('-data_emissao', '-numero_nota_fiscal')[:100]
    serializer_class = NotaFiscalEntradaListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        qs = NotaFiscalEntrada.objects.using(banco).all()
        empresa = self.request.query_params.get('empresa')
        filial = self.request.query_params.get('filial')
        cnpj = self.request.query_params.get('cnpj')

        if cnpj:
            import re
            digits = re.sub(r"\D", "", str(cnpj))
            masked = f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}" if len(digits)==14 else digits
            qs = qs.filter(Q(destinatario_cnpj__in=[digits, masked])).exclude(Q(emitente_cnpj__in=[digits, masked]))
        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)

        return qs.order_by('-data_emissao', '-numero_nota_fiscal')

    @action(detail=True, methods=['get'])
    def itens(self, request, pk=None):
        banco = get_licenca_db_config(request)
        nota = NotaFiscalEntrada.objects.using(banco).filter(pk=pk).first()
        if not nota:
            from rest_framework.response import Response
            return Response({'error': 'Nota fiscal não encontrada'}, status=404)
        itens = EntradaNFeService.listar_itens(nota_entrada=nota)
        from rest_framework.response import Response
        return Response({'itens': itens})

    @action(detail=True, methods=['get'])
    def preprocessar(self, request, pk=None):
        banco = get_licenca_db_config(request)
        nota = NotaFiscalEntrada.objects.using(banco).filter(pk=pk).first()
        if not nota:
            from rest_framework.response import Response
            return Response({'error': 'Nota fiscal não encontrada'}, status=404)
        itens = EntradaNFeService.listar_itens(nota_entrada=nota)
        sugeridos = []
        for it in itens:
            prod = None
            if it.get('ean'):
                prod = Produtos.objects.using(banco).filter(prod_coba=it['ean'], prod_empr=str(nota.empresa)).first()
            if not prod and it.get('forn_cod'):
                prod = Produtos.objects.using(banco).filter(prod_codi=it['forn_cod'], prod_empr=str(nota.empresa)).first()
            su = dict(it)
            su['produto_sugerido'] = str(prod.prod_codi) if prod else None
            su['produto_nome'] = str(prod.prod_nome) if prod else None
            sugeridos.append(su)
        from rest_framework.response import Response
        return Response({'itens': sugeridos})
