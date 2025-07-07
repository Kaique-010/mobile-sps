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

        # Adicionar debug para verificar os valores
        print(f"Debug - empresa: {empresa}, filial: {filial}, data_ini: {data_ini}, data_fim: {data_fim}")
        print(f"Debug - Headers: {dict(request.META)}")
        print(f"Debug - GET params: {dict(request.GET)}")

        if not all([empresa, filial, data_ini, data_fim]):
            return Response({
                "erro": "Parâmetros obrigatórios faltando",
                "detalhes": {
                    "empresa": empresa,
                    "filial": filial,
                    "data_ini": data_ini,
                    "data_fim": data_fim
                }
            }, status=400)

        print("Debug - Parâmetros validados com sucesso")
        
        try:
            slug = get_licenca_slug()
            print(f"Debug - Slug obtido: {slug}")

            with connections[slug].cursor() as cursor:
                print("Debug - Executando query SQL...")
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
                print(f"Debug - Query executada. Linhas retornadas: {len(rows)}")
                print(f"Debug - DataFrame criado: {df.shape}")

            print("Debug - Chamando gerar_previsao_linear...")
            resultado = gerar_previsao_linear(df, coluna_data='mes', coluna_valor='total', meses_prever=6)
            print(f"Debug - Resultado da previsão: {type(resultado)}")

            if isinstance(resultado, dict) and 'erro' in resultado:
                print(f"Debug - Erro na previsão: {resultado}")
                # Retorna 200 com mensagem informativa ao invés de 400
                return Response({
                    "mensagem": "Não há dados históricos suficientes para gerar previsões de despesas.",
                    "detalhes": "Para gerar previsões precisas, é necessário ter pelo menos 3 meses de dados históricos de despesas no período selecionado.",
                    "dados_encontrados": len(rows),
                    "periodo_consultado": f"{data_ini} a {data_fim}"
                }, status=200)

            print("Debug - Retornando resultado com sucesso")
            return Response(resultado)
            
        except Exception as e:
            print(f"Debug - Exceção capturada: {str(e)}")
            print(f"Debug - Tipo da exceção: {type(e)}")
            return Response({"erro": f"Erro interno: {str(e)}"}, status=500)


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

        # Adicionar debug para verificar os valores
        print(f"Debug LUCRO - empresa: {empresa}, filial: {filial}, data_ini: {data_ini}, data_fim: {data_fim}")
        print(f"Debug LUCRO - GET params: {dict(request.GET)}")

        if not all([empresa, filial, data_ini, data_fim]):
            print(f"Debug LUCRO - Parâmetros faltando: empresa={empresa}, filial={filial}, data_ini={data_ini}, data_fim={data_fim}")
            return Response({"erro": "Parâmetros obrigatórios faltando"}, status=400)

        print("Debug LUCRO - Parâmetros validados com sucesso")
        
        try:
            slug = get_licenca_slug()
            print(f"Debug LUCRO - Slug obtido: {slug}")

            with connections[slug].cursor() as cursor:
                print("Debug LUCRO - Executando query SQL...")
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
                print(f"Debug LUCRO - Query executada. Linhas retornadas: {len(rows)}")
                print(f"Debug LUCRO - DataFrame criado: {df.shape}")

            print("Debug LUCRO - Chamando gerar_previsao_linear...")
            resultado = gerar_previsao_linear(df, coluna_data='mes', coluna_valor='total', meses_prever=6)
            print(f"Debug LUCRO - Resultado da previsão: {type(resultado)}")

            if isinstance(resultado, dict) and 'erro' in resultado:
                print(f"Debug LUCRO - Erro na previsão: {resultado}")
                # Retorna 200 com mensagem informativa ao invés de 400
                return Response({
                    "mensagem": "Não há dados históricos suficientes para gerar previsões de lucro.",
                    "detalhes": "Para gerar previsões precisas, é necessário ter pelo menos 3 meses de dados históricos de receitas no período selecionado.",
                    "dados_encontrados": len(rows),
                    "periodo_consultado": f"{data_ini} a {data_fim}"
                }, status=200)

            print("Debug LUCRO - Retornando resultado com sucesso")
            return Response(resultado)
            
        except Exception as e:
            print(f"Debug LUCRO - Exceção capturada: {str(e)}")
            print(f"Debug LUCRO - Tipo da exceção: {type(e)}")
            return Response({"erro": f"Erro interno: {str(e)}"}, status=500)


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

        # Adicionar debug para verificar os valores
        print(f"Debug FLUXO - empresa: {empresa}, filial: {filial}, data_ini: {data_ini}, data_fim: {data_fim}")
        print(f"Debug FLUXO - GET params: {dict(request.GET)}")

        if not all([empresa, filial, data_ini, data_fim]):
            print(f"Debug FLUXO - Parâmetros faltando: empresa={empresa}, filial={filial}, data_ini={data_ini}, data_fim={data_fim}")
            return Response({"erro": "Parâmetros obrigatórios faltando"}, status=400)

        print("Debug FLUXO - Parâmetros validados com sucesso")
        
        try:
            slug = get_licenca_slug()
            print(f"Debug FLUXO - Slug obtido: {slug}")

            # 1. Receita prevista
            print("Debug FLUXO - Executando query de receita...")
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
                print(f"Debug FLUXO - Query receita executada. Linhas: {len(receita_rows)}")

            # 2. Despesa prevista
            print("Debug FLUXO - Executando query de despesa...")
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
                print(f"Debug FLUXO - Query despesa executada. Linhas: {len(despesa_rows)}")

            # Previsão
            from Gerencial.services.preditivo import gerar_previsao_linear

            print("Debug FLUXO - Gerando previsão de receita...")
            receita = gerar_previsao_linear(df_receita, 'mes', 'total', meses_prever=6)
            print(f"Debug FLUXO - Previsão receita: {type(receita)}")
            
            print("Debug FLUXO - Gerando previsão de despesa...")
            despesa = gerar_previsao_linear(df_despesa, 'mes', 'total', meses_prever=6)
            print(f"Debug FLUXO - Previsão despesa: {type(despesa)}")

            if isinstance(receita, dict) and 'erro' in receita:
                print(f"Debug FLUXO - Erro na previsão de receita: {receita}")
                return Response({
                    "mensagem": "Não há dados históricos suficientes para gerar previsões de fluxo de caixa.",
                    "detalhes": "Para gerar previsões precisas, é necessário ter pelo menos 3 meses de dados históricos de receitas e despesas no período selecionado.",
                    "dados_receita": len(receita_rows),
                    "dados_despesa": len(despesa_rows),
                    "periodo_consultado": f"{data_ini} a {data_fim}",
                    "problema": "Dados insuficientes de receita"
                }, status=200)
                
            if isinstance(despesa, dict) and 'erro' in despesa:
                print(f"Debug FLUXO - Erro na previsão de despesa: {despesa}")
                return Response({
                    "mensagem": "Não há dados históricos suficientes para gerar previsões de fluxo de caixa.",
                    "detalhes": "Para gerar previsões precisas, é necessário ter pelo menos 3 meses de dados históricos de receitas e despesas no período selecionado.",
                    "dados_receita": len(receita_rows),
                    "dados_despesa": len(despesa_rows),
                    "periodo_consultado": f"{data_ini} a {data_fim}",
                    "problema": "Dados insuficientes de despesa"
                }, status=200)

            print("Debug FLUXO - Combinando previsões...")
            # Combinar previsões por mês
            fluxo = []
            for r, d in zip(receita['previsao'], despesa['previsao']):
                fluxo.append({
                    "mes": r['mes'],
                    "receita": r['valor'],
                    "despesa": d['valor'],
                    "fluxo_liquido": round(r['valor'] - d['valor'], 2)
                })

            print("Debug FLUXO - Retornando resultado com sucesso")
            return Response({
                "fluxo_caixa_previsto": fluxo,
                "modelo": "regressao_linear",
                "erro_medio_receita": receita['erro_medio'],
                "erro_medio_despesa": despesa['erro_medio']
            })
            
        except Exception as e:
            print(f"Debug FLUXO - Exceção capturada: {str(e)}")
            print(f"Debug FLUXO - Tipo da exceção: {type(e)}")
            return Response({"erro": f"Erro interno: {str(e)}"}, status=500)
