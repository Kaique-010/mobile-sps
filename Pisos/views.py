from rest_framework import viewsets, status
from django.views.generic import TemplateView
from core.decorator import ModuloRequeridoMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
import logging
from decimal import Decimal, InvalidOperation
from django.db.models import Sum, Count
from .models import Orcamentopisos, Pedidospisos, Itensorcapisos, Itenspedidospisos                            
from .serializers import (
    OrcamentopisosSerializer, 
    PedidospisosSerializer, 
    ItensorcapisosSerializer, 
    ItenspedidospisosSerializer
)
from django.db import transaction
from core.mixins.vendedor_mixin import VendedorEntidadeMixin
from types import SimpleNamespace
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin
from Produtos.models import Produtos, Tabelaprecos
from Entidades.models import Entidades
from Pisos.services.orcamento_exportar_service import OrcamentoExportarPedidoService
from Pisos.services.metragem_service import MetragemProdutoService
from rest_framework.authentication import SessionAuthentication, BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.utils import get_db_from_slug
from Licencas.models import Usuarios, Empresas, Filiais
import logging

logger = logging.getLogger(__name__)




class CustomSessionAuthentication(BaseAuthentication):
    """
    Autenticação personalizada que evita recursão infinita
    """
    def authenticate(self, request):
        # IMPORTANTE: NÃO acessar request.user aqui pois causa recursão!
        
        # 1. Verificar se há sessão ativa com user_id
        user_id = request.session.get("usua_codi")
        if not user_id:
            return None  # Sem sessão, passa para próximo autenticador

        # 2. Obter slug
        slug = getattr(request, 'slug', None)
        if not slug:
            slug = request.session.get('slug')
        
        if not slug:
            return None  # Sem slug, não pode autenticar

        # 3. Buscar usuário no banco correto
        try:
            banco = get_db_from_slug(slug)
            user = Usuarios.objects.using(banco).get(pk=user_id)
            
            # IMPORTANTE: Definir backend manualmente para evitar problemas
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            
            logger.debug(f"[CustomSessionAuth] Usuário autenticado: {user.usua_logi} (ID: {user_id})")
            return (user, None)
            
        except Usuarios.DoesNotExist:
            logger.warning(f"[CustomSessionAuth] Usuário {user_id} não encontrado no banco {banco}")
            return None
        except Exception as e:
            logger.error(f"[CustomSessionAuth] Erro na autenticação: {e}", exc_info=True)
            return None




class BaseMultiDBModelViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    # REMOVA o CustomSessionAuthentication se não funcionar
    authentication_classes = [SessionAuthentication]  # <- Simplifique para testar
    permission_classes = [IsAuthenticated]

    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error(f"Banco de dados não encontrado para {self.__class__.__name__}")
            raise NotFound("Banco de dados não encontrado.")
        return banco

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context


class OrcamentopisosViewSet(BaseMultiDBModelViewSet, VendedorEntidadeMixin):
    modulo_necessario = 'Pisos'
    serializer_class = OrcamentopisosSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['orca_nume', 'orca_clie']
    filterset_fields = [
        'orca_empr', 'orca_fili', 'orca_nume', 'orca_clie', 
        'orca_data', 'orca_stat', 'orca_vend'
    ]
    lookup_field = 'orca_nume'
    
    def get_queryset(self):
        banco = self.get_banco()
        queryset = Orcamentopisos.objects.using(banco).all()
        queryset = self.filter_por_vendedor(queryset, 'orca_vend')
        
        # Filtros por parâmetros de query
        empresa_id = self.request.query_params.get('orca_empr')
        filial_id = self.request.query_params.get('orca_fili')
        cliente_id = self.request.query_params.get('orca_clie')
        
        if empresa_id:
            queryset = queryset.filter(orca_empr=empresa_id)
        if filial_id:
            queryset = queryset.filter(orca_fili=filial_id)
        if cliente_id:
            queryset = queryset.filter(orca_clie=cliente_id)
            
        return queryset.order_by('-orca_data', '-orca_nume')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calcular agregados para o dashboard (antes da paginação)
        try:
            # 1. Totais Gerais
            total_pedidos = queryset.count()
            total_valor_agg = queryset.aggregate(total=Sum('orca_tota'))
            total_valor = total_valor_agg['total'] or Decimal('0.00')
            
            # 2. Dados para Gráficos (Vendas por Vendedor)
            # Agrupar por vendedor e somar totais
            banco = self.get_banco()
            vendas_vendedor = queryset.values('orca_vend').annotate(total=Sum('orca_tota')).order_by('-total')[:6]
            
            sales_by_seller = {}
            seller_ids = [v['orca_vend'] for v in vendas_vendedor if v['orca_vend']]
            
            if seller_ids:
                # Buscar nomes dos vendedores
                vendedores = Entidades.objects.using(banco).filter(enti_clie__in=seller_ids).values('enti_clie', 'enti_nome')
                nome_map = {v['enti_clie']: v['enti_nome'] for v in vendedores}
                
                for item in vendas_vendedor:
                    vid = item['orca_vend']
                    if vid:
                        nome = nome_map.get(vid, f"Vendedor {vid}")
                        sales_by_seller[nome] = item['total']
            
            # 3. Total de Itens (Opcional - pode ser custoso)
            # Deixando como 0 por enquanto para não impactar performance com joins complexos em legado
            total_itens = 0
            
            aggregates = {
                'total_pedidos': total_pedidos,
                'total_valor': total_valor,
                'total_itens': total_itens,
                'sales_by_seller': sales_by_seller
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular agregados no PedidospisosViewSet: {e}", exc_info=True)
            aggregates = {}

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            # Injetar agregados na resposta paginada
            response.data.update(aggregates)
            return response

        serializer = self.get_serializer(queryset, many=True)
        # Se não houver paginação, retorna lista normal (mas dashboard espera objeto paginado geralmente)
        # Vamos retornar um dict com results e aggregates se não for paginado
        return Response({
            'results': serializer.data,
            **aggregates
        })

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        logger.info("[OrcamentopisosViewSet.create] Criando orçamento de pisos")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        orcamento = serializer.save()

        response_serializer = self.get_serializer(orcamento)
        headers = self.get_success_headers(response_serializer.data)

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

        
        
    @action(detail=False, methods=["post"])
    def exportar_pedido(self, request, empresa=None, filial=None, numero=None, slug=None):
        banco = self.get_banco()

        try:
            numero_pedido = OrcamentoExportarPedidoService().executar(
                banco=banco,
                empresa=empresa,
                filial=filial,
                numero=numero,
            )

            return Response(
                {
                    "message": "Orçamento exportado com sucesso",
                    "pedido_numero": numero_pedido,
                },
                status=status.HTTP_201_CREATED,
            )

        except Orcamentopisos.DoesNotExist:
            return Response(
                {"error": "Orçamento não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(f"Erro ao exportar: {e}", exc_info=True)
            return Response(
                {"error": "Erro interno"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PedidospisosViewSet(BaseMultiDBModelViewSet, VendedorEntidadeMixin):
    permission_classes = []
    modulo_necessario = 'Pisos'
    serializer_class = PedidospisosSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['pedi_nume', 'pedi_clie']
    filterset_fields = [
        'pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_clie', 
        'pedi_data', 'pedi_stat', 'pedi_vend', 'pedi_orca'
    ]
    lookup_field = 'pedi_nume'
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calcular agregados para o dashboard (antes da paginação)
        try:
            # 1. Totais Gerais
            total_pedidos = queryset.count()
            total_valor_agg = queryset.aggregate(total=Sum('pedi_tota'))
            total_valor = total_valor_agg['total'] or Decimal('0.00')
            
            # 2. Dados para Gráficos (Vendas por Vendedor)
            banco = self.get_banco()
            vendas_vendedor = queryset.values('pedi_vend').annotate(total=Sum('pedi_tota')).order_by('-total')[:6]
            
            sales_by_seller = {}
            seller_ids = [v['pedi_vend'] for v in vendas_vendedor if v['pedi_vend']]
            
            if seller_ids:
                vendedores = Entidades.objects.using(banco).filter(enti_clie__in=seller_ids).values('enti_clie', 'enti_nome')
                nome_map = {v['enti_clie']: v['enti_nome'] for v in vendedores}
                
                for item in vendas_vendedor:
                    vid = item['pedi_vend']
                    if vid:
                        nome = nome_map.get(vid, f"Vendedor {vid}")
                        sales_by_seller[nome] = item['total']
            
            # 3. Total de Itens (Opcional - pode ser custoso)
            total_itens = 0
            
            aggregates = {
                'total_pedidos': total_pedidos,
                'total_valor': total_valor,
                'total_itens': total_itens,
                'sales_by_seller': sales_by_seller
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular agregados no PedidospisosViewSet: {e}", exc_info=True)
            aggregates = {}

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            # Injetar agregados na resposta paginada
            response.data.update(aggregates)
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            **aggregates
        })
    
    def get_queryset(self):

        try:
            # Log dos parâmetros recebidos para debug
            logger.info(f"[PedidospisosViewSet] Params recebidos: {self.request.query_params}")

            try:
                banco = self.get_banco()
                logger.info(f"[PedidospisosViewSet] Usando banco: {banco}")
            except Exception as e:
                logger.error(f"[PedidospisosViewSet] Erro ao obter banco: {e}", exc_info=True)
                return Pedidospisos.objects.none()
            
            # 2. Criar queryset base
            try:
                queryset = Pedidospisos.objects.using(banco).all()
                logger.info(f"[PedidospisosViewSet] Queryset inicial criado, total: {queryset.count()}")
            except Exception as e:
                logger.error(f"[PedidospisosViewSet] Erro ao criar queryset base: {e}", exc_info=True)
                return Pedidospisos.objects.none()
            
            # 3. Filtrar por vendedor (com try-except para não quebrar se falhar)
            try:
                queryset = self.filter_por_vendedor(queryset, 'pedi_vend')
                logger.info(f"[PedidospisosViewSet] Após filtro vendedor: {queryset.count()}")
            except AttributeError as e:
                logger.warning(f"[PedidospisosViewSet] filter_por_vendedor não disponível: {e}")
            except Exception as e:
                logger.error(f"[PedidospisosViewSet] Erro ao filtrar vendedor: {e}", exc_info=True)
            
            # 4. Aplicar filtros de query params
            try:
                # Filtros simples
                empresa_id = self.request.query_params.get('pedi_empr')
                filial_id = self.request.query_params.get('pedi_fili')
                cliente_id = self.request.query_params.get('pedi_clie')
                
                if empresa_id:
                    queryset = queryset.filter(pedi_empr=empresa_id)
                    logger.info(f"Filtrado por empresa: {empresa_id}")
                    
                if filial_id:
                    queryset = queryset.filter(pedi_fili=filial_id)
                    logger.info(f"Filtrado por filial: {filial_id}")
                    
                if cliente_id:
                    queryset = queryset.filter(pedi_clie=cliente_id)
                    logger.info(f"Filtrado por cliente: {cliente_id}")
                
            except Exception as e:
                logger.error(f"[PedidospisosViewSet] Erro nos filtros simples: {e}", exc_info=True)
            
            # 5. Filtro por nome de cliente
            try:
                nome_cliente = self.request.query_params.get('cliente_nome')
                if nome_cliente:
                    logger.info(f"Filtrando por nome de cliente: {nome_cliente}")
                    clientes_ids = Entidades.objects.using(banco).filter(
                        enti_nome__icontains=nome_cliente
                    )
                    if empresa_id:
                        clientes_ids = clientes_ids.filter(enti_empr=empresa_id)
                    
                    clientes_list = list(clientes_ids.values_list('enti_clie', flat=True))
                    logger.debug(f"Clientes encontrados: {len(clientes_list)}")
                    
                    if clientes_list:
                        queryset = queryset.filter(pedi_clie__in=clientes_list)
                    else:
                        logger.warning(f"Nenhum cliente encontrado com nome: {nome_cliente}")
                        # Retorna vazio se não encontrou nenhum cliente com esse nome
                        queryset = queryset.none()
                        
            except Exception as e:
                logger.error(f"[PedidospisosViewSet] Erro ao filtrar por nome de cliente: {e}", exc_info=True)
            
            # 6. Filtro por nome de vendedor
            try:
                nome_vendedor = self.request.query_params.get('vendedor_nome')
                if nome_vendedor:
                    logger.info(f"Filtrando por nome de vendedor: {nome_vendedor}")
                    vendedores_ids = Entidades.objects.using(banco).filter(
                        enti_nome__icontains=nome_vendedor
                    )
                    if empresa_id:
                        vendedores_ids = vendedores_ids.filter(enti_empr=empresa_id)
                    
                    vendedores_list = list(vendedores_ids.values_list('enti_clie', flat=True))
                    logger.debug(f"Vendedores encontrados: {len(vendedores_list)}")
                    
                    if vendedores_list:
                        queryset = queryset.filter(pedi_vend__in=vendedores_list)
                    else:
                        logger.warning(f"Nenhum vendedor encontrado com nome: {nome_vendedor}")
                        queryset = queryset.none()
                        
            except Exception as e:
                logger.error(f"[PedidospisosViewSet] Erro ao filtrar por nome de vendedor: {e}", exc_info=True)
            
            # 7. Filtro por data
            try:
                from datetime import datetime
                data_ini = self.request.query_params.get('data_inicial') or self.request.query_params.get('data_inicio')
                data_fim = self.request.query_params.get('data_final') or self.request.query_params.get('data_fim')
                
                if data_ini and data_fim:
                    di = datetime.strptime(data_ini, '%Y-%m-%d').date()
                    df = datetime.strptime(data_fim, '%Y-%m-%d').date()
                    queryset = queryset.filter(pedi_data__range=(di, df))
                    logger.debug(f"Filtrado por data: {di} a {df}")
                    
                elif data_ini:
                    di = datetime.strptime(data_ini, '%Y-%m-%d').date()
                    queryset = queryset.filter(pedi_data__gte=di)
                    logger.debug(f"Filtrado por data >= {di}")
                    
                elif data_fim:
                    df = datetime.strptime(data_fim, '%Y-%m-%d').date()
                    queryset = queryset.filter(pedi_data__lte=df)
                    logger.debug(f"Filtrado por data <= {df}")
                    
            except ValueError as e:
                logger.error(f"[PedidospisosViewSet] Formato de data inválido: {e}")
            except Exception as e:
                logger.error(f"[PedidospisosViewSet] Erro ao filtrar por data: {e}", exc_info=True)
            
            # 8. Log final e retorno
            try:
                total_final = queryset.count()
                logger.info(f"[PedidospisosViewSet] Queryset final: {total_final} registros")
            except Exception as e:
                logger.error(f"[PedidospisosViewSet] Erro ao contar registros: {e}")
            
            return queryset.order_by('-pedi_data', '-pedi_nume')
            
        except Exception as e:
            # Erro crítico - loga tudo e retorna vazio
            logger.critical(
                f"[PedidospisosViewSet] ERRO CRÍTICO em get_queryset: {e}", 
                exc_info=True,
                extra={
                    'user': getattr(self.request, 'user', None),
                    'path': getattr(self.request, 'path', None),
                    'query_params': getattr(self.request, 'query_params', None),
                }
            )
            # Retorna queryset vazio ao invés de crashar com 500
            return Pedidospisos.objects.none()
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        logger.info("[PedidospisosViewSet.create] Criando pedido de pisos")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pedido = serializer.save()

        response_serializer = self.get_serializer(pedido)
        headers = self.get_success_headers(response_serializer.data)

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

class ItensorcapisosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Pisos'
    serializer_class = ItensorcapisosSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'item_empr', 'item_fili', 'item_orca', 'item_ambi', 'item_prod'
    ]
    
    def get_queryset(self):
        banco = self.get_banco()
        queryset = Itensorcapisos.objects.using(banco).all()
        
        # Filtros obrigatórios para performance
        item_empr = self.request.query_params.get('item_empr')
        item_fili = self.request.query_params.get('item_fili')
        item_orca = self.request.query_params.get('item_orca')
        
        if item_empr:
            queryset = queryset.filter(item_empr=item_empr)
        if item_fili:
            queryset = queryset.filter(item_fili=item_fili)
        if item_orca:
            queryset = queryset.filter(item_orca=item_orca)
            
        return queryset.order_by('item_ambi', 'item_nume')


class ItenspedidospisosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Pisos'
    serializer_class = ItenspedidospisosSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'item_empr', 'item_fili', 'item_pedi', 'item_ambi', 'item_prod'
    ]
    
    def get_queryset(self):
        banco = self.get_banco()
        queryset = Itenspedidospisos.objects.using(banco).all()
        
        # Filtros obrigatórios para performance
        item_empr = self.request.query_params.get('item_empr')
        item_fili = self.request.query_params.get('item_fili')
        item_pedi = self.request.query_params.get('item_pedi')
        
        if item_empr:
            queryset = queryset.filter(item_empr=item_empr)
        if item_fili:
            queryset = queryset.filter(item_fili=item_fili)
        if item_pedi:
            queryset = queryset.filter(item_pedi=item_pedi)
            
        return queryset.order_by('item_ambi', 'item_nume')



class ProdutosPisosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Pisos'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['prod_nome', 'prod_codi', 'prod_coba']
    filterset_fields = ['prod_empr']
    
    def get_queryset(self):
        banco = self.get_banco()
        return Produtos.objects.using(banco).all().order_by('prod_nome')
    
    def get_serializer_class(self):
        # Usar o serializer de produtos existente
        from Produtos.serializers import ProdutoSerializer
        return ProdutoSerializer
    
    def item_prod_nome(self, item_prod):
        try:
            banco = self.get_banco()
            produto = Produtos.objects.using(banco).filter(prod_codi=item_prod).first()
            if produto:
                return produto.prod_nome
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar nome do produto: {e}")
            return None
        
    def item_prod_unme(self, item_prod):
        try:
            banco = self.get_banco()
            produto = Produtos.objects.using(banco).filter(prod_codi=item_prod).first()
            if produto:
                return produto.prod_unme
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar unidade de medida do produto: {e}")
            return None
    
    @action(detail=False, methods=["post"])
    def calcular_metragem(self, request, slug=None):
        banco = self.get_banco()

        produto_id = request.data.get("produto_id")
        tamanho_m2 = request.data.get("tamanho_m2")
        percentual_quebra = request.data.get("percentual_quebra", 0)
        condicao = request.data.get("condicao", "0")

        if not produto_id:
            return Response(
                {"error": "produto_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not tamanho_m2:
            return Response(
                {"error": "tamanho_m2 é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            resultado = MetragemProdutoService().executar(
                banco=banco,
                produto_id=produto_id,
                tamanho_m2=tamanho_m2,
                percentual_quebra=percentual_quebra,
                condicao=condicao,
            )

            return Response(resultado)

        except Produtos.DoesNotExist:
            return Response(
                {"error": "Produto não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as exc:
            logger.error(f"Erro ao calcular metragem: {exc}", exc_info=True)
            return Response(
                {"error": "Erro ao calcular metragem"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DashPedidosPisosView(ModuloRequeridoMixin, TemplateView):
    template_name = 'ControleDeVisitas/dash_pedidos_pisos.html'
    modulo_requerido = 'controledevisitas'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        
        # Inject session data into context explicitly
        # Try multiple keys as session storage might vary
        empresa = self.request.session.get('empresa') or self.request.session.get('empresa_id') or self.request.session.get('empr_codi')
        filial = self.request.session.get('filial') or self.request.session.get('filial_id') or self.request.session.get('fili_codi')
        
        context['empresa'] = empresa
        context['filial'] = filial
        
        try:
            banco = get_db_from_slug(context['slug'])
            # Carregar listas de empresas e filiais para os filtros
            context['empresas_list'] = list(Empresas.objects.using(banco).all().values('empr_codi', 'empr_nome').order_by('empr_nome'))
            context['filiais_list'] = list(Filiais.objects.using(banco).all().values('empr_empr', 'empr_codi', 'empr_nome').order_by('empr_nome'))
        except Exception as e:
            logger.error(f"Erro ao carregar empresas/filiais: {e}")
            context['empresas_list'] = []
            context['filiais_list'] = []
        
        logger.info(f"[DashPedidosPisosView] Rendering dashboard. Slug: {context['slug']}, Empresa: {empresa}, Filial: {filial}")
        return context
