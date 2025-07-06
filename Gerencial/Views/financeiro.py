# gerencial/views/financeiro.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.middleware import get_licenca_slug
from core.decorator import modulo_necessario, ModuloRequeridoMixin

from django.db import connections
from Gerencial.services.preditivo import gerar_previsao_linear
import pandas as pd
from django.db.models.functions import TruncMonth
from django.db.models import Sum

class DespesasPrevistasView(ModuloRequeridoMixin, APIView):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Financeiro'


    @modulo_necessario('Financeiro')
    def get(self, request, *args, **kwargs):
        # Tenta pegar dos parâmetros da query string primeiro, depois dos headers
        empresa = request.GET.get("empr") or request.META.get('HTTP_X_EMPRESA')
        filial = request.GET.get("fili") or request.META.get('HTTP_X_FILIAL')
        data_ini = request.GET.get("data_ini")
        data_fim = request.GET.get("data_fim")

        if not all([empresa, filial, data_ini, data_fim]):
            return Response({"erro": "Parâmetros obrigatórios faltando"}, status=400)

        slug = get_licenca_slug()

        with connections[slug].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATE_TRUNC('month', bapa_dpag) AS mes,
                    SUM(bapa_pago) AS total
                FROM bapatitulos
                WHERE bapa_empr = %s
                  AND bapa_fili = %s
                  AND bapa_dpag BETWEEN %s AND %s
                GROUP BY 1
                ORDER BY 1
            """, [empresa, filial, data_ini, data_fim])

            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            df = pd.DataFrame(rows, columns=columns)

        resultado = gerar_previsao_linear(df, coluna_data='mes', coluna_valor='total', meses_prever=6)

        if isinstance(resultado, dict) and 'erro' in resultado:
            return Response(resultado, status=400)

        return Response(resultado)


class LucroPrevistoView(ModuloRequeridoMixin, APIView):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Financeiro'

    @modulo_necessario('Financeiro')
    def get(self, request, *args, **kwargs):
        # Tenta pegar dos parâmetros da query string primeiro, depois dos headers
        empresa = request.GET.get("empr") or request.META.get('HTTP_X_EMPRESA')
        filial = request.GET.get("fili") or request.META.get('HTTP_X_FILIAL')
        data_ini = request.GET.get("data_ini")
        data_fim = request.GET.get("data_fim")

        if not all([empresa, filial, data_ini, data_fim]):
            return Response({"erro": "Parâmetros obrigatórios faltando"}, status=400)

        slug = get_licenca_slug()

        with connections[slug].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATE_TRUNC('month', bare_dpag) AS mes,
                    SUM(bare_pago) AS total
                FROM baretitulos
                WHERE bare_empr = %s
                  AND bare_fili = %s
                  AND bare_dpag BETWEEN %s AND %s
                GROUP BY 1
                ORDER BY 1
            """, [empresa, filial, data_ini, data_fim])

            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            df = pd.DataFrame(rows, columns=columns)

        resultado = gerar_previsao_linear(df, coluna_data='mes', coluna_valor='total', meses_prever=6)

        if isinstance(resultado, dict) and 'erro' in resultado:
            return Response(resultado, status=400)

        return Response(resultado)


class FluxoCaixaPrevistoView(ModuloRequeridoMixin, APIView):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Financeiro'

    @modulo_necessario('Financeiro')
    def get(self, request, *args, **kwargs):
        # Tenta pegar dos parâmetros da query string primeiro, depois dos headers
        empresa = request.GET.get("empr") or request.META.get('HTTP_X_EMPRESA')
        filial = request.GET.get("fili") or request.META.get('HTTP_X_FILIAL')
        data_ini = request.GET.get("data_ini")
        data_fim = request.GET.get("data_fim")

        if not all([empresa, filial, data_ini, data_fim]):
            return Response({"erro": "Parâmetros obrigatórios faltando"}, status=400)

        slug = get_licenca_slug()

        # 1. Receita prevista
        with connections[slug].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATE_TRUNC('month', bare_dpag) AS mes,
                    SUM(bare_pago) AS total
                FROM baretitulos
                WHERE bare_empr = %s
                  AND bare_fili = %s
                  AND bare_dpag BETWEEN %s AND %s
                GROUP BY 1
                ORDER BY 1
            """, [empresa, filial, data_ini, data_fim])
            receita_rows = cursor.fetchall()
            receita_cols = [col[0] for col in cursor.description]
            df_receita = pd.DataFrame(receita_rows, columns=receita_cols)

        # 2. Despesa prevista
        with connections[slug].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATE_TRUNC('month', bapa_dpag) AS mes,
                    SUM(bapa_pago) AS total
                FROM bapatitulos
                WHERE bapa_empr = %s
                  AND bapa_fili = %s
                  AND bapa_dpag BETWEEN %s AND %s
                GROUP BY 1
                ORDER BY 1
            """, [empresa, filial, data_ini, data_fim])
            despesa_rows = cursor.fetchall()
            despesa_cols = [col[0] for col in cursor.description]
            df_despesa = pd.DataFrame(despesa_rows, columns=despesa_cols)

        # Previsão
        from Gerencial.services.preditivo import gerar_previsao_linear

        receita = gerar_previsao_linear(df_receita, 'mes', 'total', meses_prever=6)
        despesa = gerar_previsao_linear(df_despesa, 'mes', 'total', meses_prever=6)

        if 'erro' in receita:
            return Response({"erro": f"Receita: {receita['erro']}"}, status=400)
        if 'erro' in despesa:
            return Response({"erro": f"Despesa: {despesa['erro']}"}, status=400)

        # Combinar previsões por mês
        fluxo = []
        for r, d in zip(receita['previsao'], despesa['previsao']):
            fluxo.append({
                "mes": r['mes'],
                "receita": r['valor'],
                "despesa": d['valor'],
                "fluxo_liquido": round(r['valor'] - d['valor'], 2)
            })

        return Response({
            "fluxo_caixa_previsto": fluxo,
            "modelo": "regressao_linear",
            "erro_medio_receita": receita['erro_medio'],
            "erro_medio_despesa": despesa['erro_medio']
        })
