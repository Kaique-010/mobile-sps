from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from django.db import connections
from core.middleware import get_licenca_slug

class DREGerencialDinamicoView(ModuloRequeridoMixin, APIView):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Financeiro'

    @modulo_necessario('Financeiro')
    def get(self, request, *args, **kwargs):
        data_ini = request.GET.get("data_ini")
        data_fim = request.GET.get("data_fim")
        empresa = request.GET.get("empr")
        filial = request.GET.get("fili")
        slug = get_licenca_slug()

        if not all([data_ini, data_fim, empresa, filial]):
            return Response({"erro": "Parâmetros obrigatórios faltando"}, status=400)

        with connections[slug].cursor() as cursor:
            cursor.execute("""
                WITH 
                    params AS (
                        SELECT %s::int AS empresa, %s::int AS filial
                    ),
                    faturamento AS (
                        SELECT
                            n.empresa,
                            n.filial,
                            SUM(i.total_item) AS receita_bruta
                        FROM nf_nota n
                        JOIN nf_nota_item i ON i.nota_id = n.id
                        JOIN params p ON p.empresa = n.empresa AND p.filial = n.filial
                        WHERE n.status = 100
                          AND n.data_emissao BETWEEN %s AND %s
                          AND n.finalidade <> 4
                          AND i.cfop::text !~ '^(12|52|22|62)'
                        GROUP BY n.empresa, n.filial
                    ),
                    devolucoes AS (
                        SELECT
                            n.empresa,
                            n.filial,
                            SUM(i.total_item) AS total_devolvido
                        FROM nf_nota n
                        JOIN nf_nota_item i ON i.nota_id = n.id
                        JOIN params p ON p.empresa = n.empresa AND p.filial = n.filial
                        WHERE n.status = 100
                          AND n.data_emissao BETWEEN %s AND %s
                          AND (n.finalidade = 4 OR i.cfop::text ~ '^(12|52|22|62)')
                        GROUP BY n.empresa, n.filial
                    ),
                recebimentos AS (
                    SELECT 
                        bare_empr AS empresa,
                        bare_fili AS filial,
                        SUM(bare_pago) AS total_recebido
                    FROM baretitulos
                    JOIN params p ON p.empresa = bare_empr AND p.filial = bare_fili
                    WHERE bare_dpag BETWEEN %s AND %s
                    GROUP BY bare_empr, bare_fili
                ),
                despesas AS (
                    SELECT 
                        bapa_empr AS empresa,
                        bapa_fili AS filial,
                        SUM(bapa_pago) AS total_despesas
                    FROM bapatitulos
                    JOIN params p ON p.empresa = bapa_empr AND p.filial = bapa_fili
                    WHERE bapa_dpag BETWEEN %s AND %s
                    GROUP BY bapa_empr, bapa_fili
                )
                SELECT
                    p.empresa,
                    p.filial,
                    COALESCE(f.receita_bruta, 0) AS receita_bruta,
                    COALESCE(d.total_devolvido, 0) AS deducoes,
                    (COALESCE(f.receita_bruta, 0) - COALESCE(d.total_devolvido, 0)) AS receita_liquida,
                    (COALESCE(f.receita_bruta, 0) * 0.403) AS cmv,
                    ((COALESCE(f.receita_bruta, 0) - COALESCE(d.total_devolvido, 0)) - (COALESCE(f.receita_bruta, 0) * 0.403)) AS lucro_bruto,
                    COALESCE(r.total_recebido, 0) AS total_recebido,
                    COALESCE(dp.total_despesas, 0) AS total_despesas,
                    (COALESCE(r.total_recebido, 0) - COALESCE(dp.total_despesas, 0)) AS resultado_operacional
                FROM params p
                LEFT JOIN faturamento f ON f.empresa = p.empresa AND f.filial = p.filial
                LEFT JOIN devolucoes d ON d.empresa = p.empresa AND d.filial = p.filial
                LEFT JOIN recebimentos r ON r.empresa = p.empresa AND r.filial = p.filial
                LEFT JOIN despesas dp ON dp.empresa = p.empresa AND dp.filial = p.filial
            """, [
                empresa, filial,
                data_ini, data_fim,
                data_ini, data_fim,
                data_ini, data_fim,
                data_ini, data_fim,
            ])

            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                data = dict(zip(columns, row))
                return Response(data)
            else:
                return Response({}, status=200)



class DRECaixaView(ModuloRequeridoMixin, APIView):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Financeiro'

    @modulo_necessario('Financeiro')
    def get(self, request, *args, **kwargs):
        data_ini = request.GET.get("data_ini")
        data_fim = request.GET.get("data_fim")
        empresa = request.GET.get("empr")
        filial = request.GET.get("fili")

        if not all([data_ini, data_fim, empresa, filial]):
            return Response({"erro": "Parâmetros obrigatórios faltando"}, status=400)

        slug = get_licenca_slug()

        with connections[slug].cursor() as cursor:
            cursor.execute("""
                WITH recebimentos AS (
                    SELECT 
                        bare_empr AS empresa,
                        bare_fili AS filial,
                        SUM(bare_pago) AS total_recebido
                    FROM baretitulos
                    WHERE bare_dpag BETWEEN %s AND %s
                    GROUP BY bare_empr, bare_fili
                ),
                despesas AS (
                    SELECT 
                        bapa_empr AS empresa,
                        bapa_fili AS filial,
                        SUM(bapa_pago) AS total_despesas
                    FROM bapatitulos
                    WHERE bapa_dpag BETWEEN %s AND %s
                    GROUP BY bapa_empr, bapa_fili
                )
                SELECT 
                    r.empresa, r.filial,
                    COALESCE(r.total_recebido, 0) AS total_recebido,
                    COALESCE(d.total_despesas, 0) AS total_despesas,
                    (COALESCE(r.total_recebido, 0) - COALESCE(d.total_despesas, 0)) AS resultado_caixa
                FROM recebimentos r
                LEFT JOIN despesas d ON d.empresa = r.empresa AND d.filial = r.filial
                WHERE r.empresa = %s AND r.filial = %s
            """, [
                data_ini, data_fim,
                data_ini, data_fim,
                empresa, filial
            ])

            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                data = dict(zip(columns, row))
                return Response(data)
            else:
                return Response({}, status=200)
