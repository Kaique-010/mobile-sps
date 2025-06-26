from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from .models import OrcamentoAnaliticoView
from .serializers import OrcamentoAnaliticoSerializer
from django.db import connections
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from Entidades.models import Entidades
from contas_a_pagar.models import Bapatitulos, Titulospagar
from contas_a_receber.models import Baretitulos, Titulosreceber
from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug


#Operario Fluco de caixa 
class DashboardFinanceiroView(ModuloRequeridoMixin, APIView):
    modulo_necessario = 'Dashboard'

    def get(self, request, slug=None):
        slug = get_licenca_slug()
        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        empresa_id = request.headers.get("X-Empresa")
        filial_id = request.headers.get("X-Filial")
        data_ini = request.query_params.get('data_ini')
        data_fim = request.query_params.get('data_fim')
        saldo_inicial = request.query_params.get('saldo_inicial', '0.00')

        try:
            data_ini = datetime.strptime(data_ini, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            saldo_inicial = Decimal(saldo_inicial)
        except Exception:
            return Response({"error": "Parâmetros inválidos."}, status=status.HTTP_400_BAD_REQUEST)


        recebimentos_agrupados = (
            Baretitulos.objects.using(slug)
            .filter(
                bare_empr=empresa_id,
                bare_fili=filial_id,
                bare_dpag__range=(data_ini, data_fim)
            )
            .annotate(mes=TruncMonth('bare_dpag'))
            .values('mes', 'bare_clie')
            .annotate(valor=Sum('bare_pago'))
        )

        pagamentos_agrupados = (
            Bapatitulos.objects.using(slug)
            .filter(
                bapa_empr=empresa_id,
                bapa_fili=filial_id,
                bapa_dpag__range=(data_ini, data_fim)
            )
            .annotate(mes=TruncMonth('bapa_dpag'))
            .values('mes', 'bapa_forn')
            .annotate(valor=Sum('bapa_pago'))
        )

        ent_ids = set([r['bare_clie'] for r in recebimentos_agrupados] + [p['bapa_forn'] for p in pagamentos_agrupados])
        entidades = Entidades.objects.using(slug).filter(enti_clie__in=ent_ids).values('enti_clie', 'enti_nome')
        nomes = {e['enti_clie']: e['enti_nome'] for e in entidades}

        recebimentos = []
        pagamentos = []
        total_recebido = Decimal('0.00')
        total_pago = Decimal('0.00')

        for r in recebimentos_agrupados:
            valor = r['valor'] or Decimal('0.00')
            total_recebido += valor
            recebimentos.append({
                "mes": r['mes'].strftime('%Y-%m'),
                "entidade": nomes.get(r['bare_clie'], 'Desconhecido'),
                "valor": str(valor)
            })

        for p in pagamentos_agrupados:
            valor = p['valor'] or Decimal('0.00')
            total_pago += valor
            pagamentos.append({
                "mes": p['mes'].strftime('%Y-%m'),
                "entidade": nomes.get(p['bapa_forn'], 'Desconhecido'),
                "valor": str(valor)
            })

        saldo = saldo_inicial + total_recebido - total_pago

        return Response({
            "periodo": f"{data_ini.strftime('%Y-%m')} até {data_fim.strftime('%Y-%m')}",
            "saldo_inicial": str(saldo_inicial),
            "recebimentos": recebimentos,
            "pagamentos": pagamentos,
            "totais": {
                "total_recebido": str(total_recebido),
                "total_pago": str(total_pago),
                "saldo_final": str(saldo)
            }
        })



class OrcamentoAnaliticoViewSet(ModuloRequeridoMixin, viewsets.ReadOnlyModelViewSet):
    modulo_necessario = 'Dashboard'
    serializer_class = OrcamentoAnaliticoSerializer
    filterset_fields = ('tipo', 'plan_redu', 'mes')
    
    def get_queryset(self):
        slug = get_licenca_slug()
        if not slug:
            return OrcamentoAnaliticoView.objects.none()
        return OrcamentoAnaliticoView.objects.using(slug).all()