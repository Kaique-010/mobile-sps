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
def classificar_grupo(conta_reduzida):
    conta_str = str(conta_reduzida)
    if conta_str.startswith('3'):
        return 'Receitas'
    elif conta_str.startswith('4'):
        return 'Despesas'
    elif conta_str.startswith('1'):
        return 'Ativo'
    elif conta_str.startswith('2'):
        return 'Passivo'
    else:
        return 'Outros'

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

        with connections[slug].cursor() as cursor:
            cursor.execute("""
                SELECT plan_cont, plan_nome, mes_num, mes_nome, valor_previsto
                FROM vw_orcamento_por_mes
                WHERE plan_exer = EXTRACT(YEAR FROM %s)
            """, [data_ini])
            rows = cursor.fetchall()

        detalhamento = defaultdict(lambda: defaultdict(list))
        resumo = defaultdict(lambda: {
            "Receitas": {"previsto": 0, "realizado": 0},
            "Despesas": {"previsto": 0, "realizado": 0},
            "Ativo": {"previsto": 0, "realizado": 0},
            "Passivo": {"previsto": 0, "realizado": 0},
            "Outros": {"previsto": 0, "realizado": 0}
        })

        # Processar orçamento
        for row in rows:
            conta = str(row[0])
            nome = row[1]
            mes_num = int(row[2])
            mes_nome = row[3]
            previsto = float(row[4] or 0)
            grupo = classificar_grupo(conta)

            detalhamento[mes_nome][grupo].append({
                "conta": conta,
                "nome": nome,
                "valor_previsto": previsto,
                "valor_realizado": 0.0,
                "diferenca": 0.0
            })

            resumo[mes_nome][grupo]["previsto"] += previsto

        # Buscar realizados por conta e mês
        realizados_receitas = defaultdict(float)
        realizados_despesas = defaultdict(float)
        realizados_ativos = defaultdict(float)
        realizados_passivo = defaultdict(float)

        # Recebimentos por conta
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
            valor = float(r['valor'] or 0)
            mes_num = int(r['mes'].strftime('%m'))
            conta = str(r['bare_cont'])
            chave = (mes_num, conta)
            realizados_receitas[chave] += valor

        # Pagamentos por conta
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
            valor = float(p['valor'] or 0)
            mes_num = int(p['mes'].strftime('%m'))
            conta = str(p['bapa_cont'])
            chave = (mes_num, conta)
            realizados_despesas[chave] += valor

        # Fazer match direto por conta
        for mes_nome in detalhamento:
            mes_num = next(
                (int(r[2]) for r in rows if r[3] == mes_nome),
                None
            )
            
            if mes_num is not None:
                for grupo in detalhamento[mes_nome]:
                    for item in detalhamento[mes_nome][grupo]:
                        conta = item['conta']
                        chave = (mes_num, conta)
                        
                        if grupo == 'Receitas':
                            realizado = realizados_receitas.get(chave, 0.0)
                        elif grupo == 'Despesas':
                            realizado = realizados_despesas.get(chave, 0.0)
                        elif grupo == 'Ativo':
                            realizado = realizados_ativos.get(chave, 0.0)
                        elif grupo == 'Passivo':
                            realizado = realizados_passivo.get(chave, 0.0)
                        else:
                            realizado = 0.0
                        
                        item['valor_realizado'] = round(realizado, 2)
                        item['diferenca'] = round(item['valor_previsto'] - realizado, 2)
                        resumo[mes_nome][grupo]["realizado"] += realizado

        # Criar resumo mensal final
        resumo_mensal = {}
        for mes, grupos in resumo.items():
            receitas = grupos.get("Receitas", {"previsto": 0, "realizado": 0})
            print (receitas)

            despesas = grupos.get("Despesas", {"previsto": 0, "realizado": 0})
            print (despesas)

            ativo = grupos.get("Ativo", {"previsto": 0, "realizado": 0})
            print (ativo)

            passivo = grupos.get("Passivo", {"previsto": 0, "realizado": 0})
            print (passivo)


            saldo_previsto = receitas["previsto"] - despesas["previsto"]
            saldo_realizado = receitas["realizado"] - despesas["realizado"]

            def pct(real, prev):
                return round((real / prev) * 100, 2) if prev > 0 else None

            resumo_mensal[mes] = {
                "Receitas": {
                    "previsto": round(receitas["previsto"], 2),
                    "realizado": round(receitas["realizado"], 2),
                    "percentual": pct(receitas["realizado"], receitas["previsto"])
                },
                "Despesas": {
                    "previsto": round(despesas["previsto"], 2),
                    "realizado": round(despesas["realizado"], 2),
                    "percentual": pct(despesas["realizado"], despesas["previsto"])
                },
                "saldo_previsto": round(saldo_previsto, 2),
                "saldo_realizado": round(saldo_realizado, 2)
            }

        return Response({
            "detalhamento": dict(detalhamento),
            "resumo_mensal": resumo_mensal
        })