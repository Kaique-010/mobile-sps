from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.db import connections
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework import status
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


#com contas Operario
class OrcamentoRealizadoView(APIView):
    def get(self, request, slug=None):
        slug = get_licenca_slug()
        if not slug:
            return Response({"error": "Licença não encontrada."}, status=404)

        empresa_id = request.headers.get("X-Empresa")
        filial_id = request.headers.get("X-Filial")
        data_ini = request.query_params.get('data_ini')
        data_fim = request.query_params.get('data_fim')

        try:
            data_ini = datetime.strptime(data_ini, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except Exception:
            return Response({"error": "Parâmetros inválidos."}, status=400)

        #  Orçamentos por conta e mês
        with connections[slug].cursor() as cursor:
            cursor.execute("""
                SELECT plan_cont, plan_nome, mes_num, mes_nome, valor_previsto
                FROM vw_orcamento_por_mes
                WHERE plan_exer = EXTRACT(YEAR FROM %s)
            """, [data_ini])
            rows = cursor.fetchall()

        orcamento = defaultdict(dict)
        for conta, nome, mes_num, mes_nome, valor_previsto in rows:
            conta = str(conta)
            orcamento[mes_nome][conta] = {
                "nome": nome,
                "previsto": float(valor_previsto or 0),
                "realizado": 0.0,
                "diferenca": 0.0,
            }

        def mes_nome(dt):
            return dt.strftime('%B').capitalize()

        #  Receitas
        recebimentos = Baretitulos.objects.using(slug).filter(
            bare_empr=empresa_id,
            bare_fili=filial_id,
            bare_dpag__range=(data_ini, data_fim)
        ).annotate(
            mes=TruncMonth('bare_dpag')
        ).values(
            'mes', 'bare_cont'
        ).annotate(
            valor=Sum('bare_pago')
        )

        for r in recebimentos:
            conta = str(r['bare_cont'])
            mes = mes_nome(r['mes'])
            valor = float(r['valor'] or 0)
            if conta in orcamento[mes]:
                orcamento[mes][conta]['realizado'] += valor

        # Despesas
        pagamentos = Bapatitulos.objects.using(slug).filter(
            bapa_empr=empresa_id,
            bapa_fili=filial_id,
            bapa_dpag__range=(data_ini, data_fim)
        ).annotate(
            mes=TruncMonth('bapa_dpag')
        ).values(
            'mes', 'bapa_cont'
        ).annotate(
            valor=Sum('bapa_pago')
        )

        for p in pagamentos:
            conta = str(p['bapa_cont'])
            mes = mes_nome(p['mes'])
            valor = float(p['valor'] or 0)
            if conta in orcamento[mes]:
                orcamento[mes][conta]['realizado'] -= valor  

        resumo_mensal = {}
        for mes in orcamento:
            total_previsto = 0.0
            total_realizado = 0.0

            for conta in orcamento[mes]:
                item = orcamento[mes][conta]
                item['realizado'] = round(item['realizado'], 2)
                item['diferenca'] = round(item['realizado'] - item['previsto'], 2)

                total_previsto += item['previsto']
                total_realizado += item['realizado']

            percentual = round((total_realizado / total_previsto) * 100, 2) if total_previsto else None
            saldo = round(total_realizado - total_previsto, 2)

            resumo_mensal[mes] = {
                "total_previsto": round(total_previsto, 2),
                "total_realizado": round(total_realizado, 2),
                "saldo": saldo,
                "percentual_execucao": percentual
            }

        return Response({
            "detalhamento": dict(orcamento),
            "resumo_mensal": resumo_mensal
        })