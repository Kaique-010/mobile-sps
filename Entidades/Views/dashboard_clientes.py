from django.db import connections
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from .base_cliente import IsCliente
from Pedidos.models import PedidoVenda, Itenspedidovenda
from Orcamentos.models import Orcamentos, ItensOrcamento
from O_S.models import OrdemServicoGeral, Os
from OrdemdeServico.models import Ordemservico
from django.db.models import Sum, Q, Case, When, Value, DateField
from rest_framework.permissions import IsAuthenticated
from core.middleware import get_licenca_slug
from django.core.cache import cache
import logging



class ClienteDashboardViewSet(viewsets.ViewSet): 
    permission_classes = [IsCliente]
    logger = logging.getLogger(__name__)

    def _cache_key(self, banco, cliente_id, ver_preco):
        return f"dash:cliente:b={banco}|c={cliente_id}|vp={'1' if ver_preco else '0'}"

    def _should_refresh(self, request):
        val = (request.query_params.get('refresh') or '').strip().lower()
        return val in ('1', 'true', 'yes', 'y')

    def _get_safe_ordemservico_totals(self, banco, cliente_id):
        """Retorna totais de Ordemservico usando SQL puro para evitar erros de data no Django"""
        count = 0
        total = 0
        try:
            with connections[banco].cursor() as cursor:
                # Contagem
                query_count = """
                    SELECT COUNT(*) 
                    FROM ordemservico 
                    WHERE orde_enti = %s 
                      AND orde_seto IS NOT NULL AND orde_seto != 0
                      AND orde_stat_orde IN (0, 1, 3)
                      AND (EXTRACT(YEAR FROM orde_data_aber) BETWEEN 2020 AND 2100)
                """
                cursor.execute(query_count, [cliente_id])
                row = cursor.fetchone()
                if row:
                    count = row[0]

                # Soma
                query_sum = """
                    SELECT SUM(orde_tota) 
                    FROM ordemservico 
                    WHERE orde_enti = %s 
                      AND orde_seto IS NOT NULL AND orde_seto != 0
                      AND orde_stat_orde IN (0, 1, 3)
                      AND (EXTRACT(YEAR FROM orde_data_aber) BETWEEN 2020 AND 2100)
                """
                cursor.execute(query_sum, [cliente_id])
                row = cursor.fetchone()
                if row and row[0] is not None:
                    total = row[0]
        except Exception as e:
            print(f"Erro em _get_safe_ordemservico_totals: {e}")
            
        return count, total

    def _get_safe_os_totals(self, banco, cliente_id):
        """Retorna totais de Os usando SQL puro e verificando colunas existentes"""
        count = 0
        total = 0
        try:
            with connections[banco].cursor() as cursor:
                # Verifica se a tabela existe (opcional, mas seguro)
                cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'os'")
                if not cursor.fetchone():
                    return 0, 0

                # Verifica se os_tota existe
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'os' AND column_name = 'os_tota'")
                has_os_tota = cursor.fetchone() is not None

                # Verifica se os_data_aber existe (assumindo que sim, mas por segurança)
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'os' AND column_name = 'os_data_aber'")
                has_os_data_aber = cursor.fetchone() is not None

                where_clauses = [
                    "os_clie = %s",
                    "os_stat_os IN (0, 1, 3)"
                ]
                
                if has_os_data_aber:
                    where_clauses.append("(EXTRACT(YEAR FROM os_data_aber) BETWEEN 2020 AND 2100)")
                
                where_str = " AND ".join(where_clauses)
                
                # Contagem
                query_count = f"SELECT COUNT(*) FROM os WHERE {where_str}"
                cursor.execute(query_count, [cliente_id])
                row = cursor.fetchone()
                if row:
                    count = row[0]

                # Soma
                if has_os_tota:
                    query_sum = f"SELECT SUM(os_tota) FROM os WHERE {where_str}"
                    cursor.execute(query_sum, [cliente_id])
                    row = cursor.fetchone()
                    if row and row[0] is not None:
                        total = row[0]
        except Exception as e:
            print(f"Erro em _get_safe_os_totals: {e}")

        return count, total

    def _get_safe_ordemservico_qs(self, banco, cliente_id):
        """Retorna queryset de Ordemservico com filtros de data segura"""
        qs = Ordemservico.objects.using(banco).filter(orde_enti=cliente_id)
        
        # Deferir campos originais para garantir que não sejam selecionados em sua forma bruta (que causa erro)
        # O extra abaixo irá re-selecionar versões seguras (texto) desses campos
        qs = qs.defer(
            'orde_data_aber', 'orde_hora_aber', 
            'orde_data_fech', 'orde_hora_fech',
            'orde_nf_data', 'orde_ulti_alte', 'orde_data_repr'
        )

        # Filtros de negocio (igual ao viewset)
        qs = qs.filter(orde_seto__isnull=False).exclude(orde_seto=0)
        
        qs = qs.filter(orde_stat_orde__in=[0, 1, 3])

        # Blindagem total via SQL puro — sem Case/When que avalia campos inválidos
        # CAST para TEXT impede psycopg2 de converter datas inválidas
        qs = qs.extra(
            where=[
                "EXTRACT(YEAR FROM orde_data_aber) BETWEEN 2020 AND 2100",
                "orde_data_fech IS NULL OR EXTRACT(YEAR FROM orde_data_fech) BETWEEN 2020 AND 2100",
                "orde_nf_data IS NULL OR EXTRACT(YEAR FROM orde_nf_data) BETWEEN 2020 AND 2100",
                "orde_ulti_alte IS NULL OR EXTRACT(YEAR FROM orde_ulti_alte) BETWEEN 2020 AND 2100",
                "orde_data_repr IS NULL OR EXTRACT(YEAR FROM orde_data_repr) BETWEEN 2020 AND 2100",
            ],
            select={
                'orde_data_aber': "CASE WHEN EXTRACT(YEAR FROM orde_data_aber) BETWEEN 2020 AND 2100 THEN orde_data_aber::text ELSE NULL END",
                'orde_hora_aber': "orde_hora_aber::text",
                'orde_data_fech': "CASE WHEN orde_data_fech IS NULL OR EXTRACT(YEAR FROM orde_data_fech) BETWEEN 2020 AND 2100 THEN orde_data_fech::text ELSE NULL END",
                'orde_hora_fech': "orde_hora_fech::text",
                'orde_nf_data':   "CASE WHEN orde_nf_data IS NULL OR EXTRACT(YEAR FROM orde_nf_data) BETWEEN 2020 AND 2100 THEN orde_nf_data::text ELSE NULL END",
                'orde_ulti_alte': "CASE WHEN orde_ulti_alte IS NULL OR EXTRACT(YEAR FROM orde_ulti_alte) BETWEEN 2020 AND 2100 THEN orde_ulti_alte::text ELSE NULL END",
                'orde_data_repr': "CASE WHEN orde_data_repr IS NULL OR EXTRACT(YEAR FROM orde_data_repr) BETWEEN 2020 AND 2100 THEN orde_data_repr::text ELSE NULL END",
                'safe_data_aber': "CASE WHEN EXTRACT(YEAR FROM orde_data_aber) BETWEEN 2020 AND 2100 THEN orde_data_aber::text ELSE NULL END",
            }
        )
        print("Query:", qs.query, qs)
        return qs

    def _get_safe_os_qs(self, banco, cliente_id):
        """Retorna queryset de Os com filtros de data segura"""
        qs = Os.objects.using(banco).filter(os_clie=cliente_id)
        
        # Deferir campos originais para garantir que não sejam selecionados em sua forma bruta
        # Também deferir campos que podem não existir em alguns bancos (ex: os_tota, os_seto) para evitar ProgrammingError
        qs = qs.defer(
            'os_data_aber', 'os_hora_aber', 
            'os_data_fech', 'os_data_entr',
            'field_log_data', 'field_log_time',
            'os_tota', 'os_seto', 'os_assi_clie', 'os_assi_oper'
        )
        
        # Filtros de negocio para Os (baseado no viewset)
        # Status equivalentes em Os: 0=Aberta, 1=Orcamento, 2=Aguardando, 21=Atraso
        qs = qs.filter(os_stat_os__in=[0, 1, 3])

        # Blindagem total via SQL puro para Os
        # CAST para TEXT impede psycopg2 de converter datas inválidas
        qs = qs.extra(
            where=[
                "EXTRACT(YEAR FROM os_data_aber) BETWEEN 2020 AND 2100",
                "os_data_fech IS NULL OR EXTRACT(YEAR FROM os_data_fech) BETWEEN 2020 AND 2100",
                "os_data_entr IS NULL OR EXTRACT(YEAR FROM os_data_entr) BETWEEN 2020 AND 2100",
            ],
            select={
                'os_data_aber': "CASE WHEN EXTRACT(YEAR FROM os_data_aber) BETWEEN 2020 AND 2100 THEN os_data_aber::text ELSE NULL END",
                'os_hora_aber': "os_hora_aber::text",
                'os_data_fech': "CASE WHEN os_data_fech IS NULL OR EXTRACT(YEAR FROM os_data_fech) BETWEEN 2020 AND 2100 THEN os_data_fech::text ELSE NULL END",
                'os_data_entr': "CASE WHEN os_data_entr IS NULL OR EXTRACT(YEAR FROM os_data_entr) BETWEEN 2020 AND 2100 THEN os_data_entr::text ELSE NULL END",
                'safe_data_aber': "CASE WHEN EXTRACT(YEAR FROM os_data_aber) BETWEEN 2020 AND 2100 THEN os_data_aber::text ELSE NULL END",
                # Adicionando tratamento para field_log se existirem no model Os (normalmente existem)
                'field_log_data': "CASE WHEN field_log_data IS NULL OR EXTRACT(YEAR FROM field_log_data) BETWEEN 2020 AND 2100 THEN field_log_data::text ELSE NULL END",
                'field_log_time': "field_log_time::text",
            }
        )
        return qs
    
    def list(self, request, slug=None):
        print("DEBUG cliente_id:", getattr(request, 'cliente_id', 'NÃO EXISTE'))
        print("DEBUG banco:", getattr(request, 'banco', 'NÃO EXISTE'))
        print("DEBUG slug:", get_licenca_slug())
        cliente_id = request.cliente_id
        banco = request.banco
        slug = get_licenca_slug()
        
        ver_preco = True
        permissoes = getattr(request, 'permissoes', {})
        if permissoes:
             ver_preco = permissoes.get('ver_preco', False)

        key = self._cache_key(banco, cliente_id, ver_preco)
        if not self._should_refresh(request):
            cached = cache.get(key)
            if cached is not None:
                try:
                    self.logger.info(f"[CACHE HIT][DASH] key={key}")
                except Exception:
                    pass
                return Response(cached)
        
        if False:
            total_ordens_servico, total_valor_ordens_servico = self._get_safe_ordemservico_totals(banco, cliente_id)
            total_os, total_valor_os = self._get_safe_os_totals(banco, cliente_id)
            
            total_valor_total = total_valor_ordens_servico + total_valor_os
            total_valor_total = round(total_valor_total, 2)

            dashboard_data = {
                'total_pedidos': 0,
                'total_orcamentos': 0, 
                'total_ordens_servico': total_ordens_servico,
                'total_os': total_os,
                'total_itens_pedidos': 0,
                'total_itens_orcamentos': 0,
                'total_valor_pedidos': 0,
                'total_valor_orcamentos': 0,
                'total_valor_ordens_servico': total_valor_ordens_servico,
                'total_valor_os': total_valor_os,
                'total_valor_total': total_valor_total, 
            }
            cache.set(key, dashboard_data)
            try:
                self.logger.info(f"[CACHE SET][DASH] key={key}")
            except Exception:
                pass
            return Response(dashboard_data)
        
        # Fluxo padrão para outros clientes
        total_pedidos = PedidoVenda.objects.using(banco).filter(pedi_forn=cliente_id).count()
        total_orcamentos = Orcamentos.objects.using(banco).filter(pedi_forn=cliente_id).count()
        
        qs_ordemservico = self._get_safe_ordemservico_qs(banco, cliente_id)
        qs_os = self._get_safe_os_qs(banco, cliente_id)
        
        total_ordens_servico = qs_ordemservico.count()
        total_os = qs_os.count()
        total_itens_pedidos = Itenspedidovenda.objects.using(banco).filter(iped_forn=cliente_id).count()
        total_itens_orcamentos = ItensOrcamento.objects.using(banco).filter(iped_forn=cliente_id).count()
        total_valor_pedidos = Itenspedidovenda.objects.using(banco).filter(iped_forn=cliente_id).aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0
        total_valor_orcamentos = ItensOrcamento.objects.using(banco).filter(iped_forn=cliente_id).aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0
        try:
            total_valor_ordens_servico = qs_ordemservico.aggregate(Sum('orde_tota'))['orde_tota__sum'] or 0
        except Exception:
            total_valor_ordens_servico = 0
            
        try:
            total_valor_os = qs_os.aggregate(Sum('os_tota'))['os_tota__sum'] or 0
        except Exception:
            total_valor_os = 0
        total_valor_total = total_valor_pedidos + total_valor_orcamentos + total_valor_ordens_servico + total_valor_os
        total_valor_total = round(total_valor_total, 2)

        if not ver_preco:
            total_valor_pedidos = 0
            total_valor_orcamentos = 0
            total_valor_ordens_servico = 0
            total_valor_os = 0
            total_valor_total = 0

        dashboard_data = {
            'total_pedidos': total_pedidos,
            'total_orcamentos': total_orcamentos, 
            'total_ordens_servico': total_ordens_servico,
            'total_os': total_os,
            'total_itens_pedidos': total_itens_pedidos,
            'total_itens_orcamentos': total_itens_orcamentos,
            'total_valor_pedidos': total_valor_pedidos,
            'total_valor_orcamentos': total_valor_orcamentos,
            'total_valor_ordens_servico': total_valor_ordens_servico,
            'total_valor_os': total_valor_os,
            'total_valor_total': total_valor_total, 
        }
        
        cache.set(key, dashboard_data)
        try:
            self.logger.info(f"[CACHE SET][DASH] key={key}")
        except Exception:
            pass
        return Response(dashboard_data)










