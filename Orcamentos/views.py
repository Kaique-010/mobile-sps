import logging
from django.db import transaction
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from .models import Orcamentos, ItensOrcamento
from .serializers import OrcamentosSerializer
from Entidades.models import Entidades
from Licencas.models import Empresas
from Pedidos.models import PedidoVenda, Itenspedidovenda
from core.utils import get_licenca_db_config
from parametros_admin.utils_pedidos import obter_parametros_pedidos, atualizar_parametros_pedidos

logger = logging.getLogger('Orcamentos')

class OrcamentoViewSet(viewsets.ModelViewSet):
    serializer_class = OrcamentosSerializer
    lookup_field = 'pedi_nume'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['pedi_forn', 'pedi_nume']
    filterset_fields = ['pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_forn', 'pedi_data']

    def get_queryset(self):
        from datetime import datetime
        
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
            
        # Base queryset otimizada
        queryset = Orcamentos.objects.using(banco).all()
        
        # Obter parâmetros de filtro
        cliente_nome = self.request.query_params.get('cliente_nome')
        numero_orcamento = self.request.query_params.get('pedi_nume')
        empresa_id = self.request.query_params.get('pedi_empr')
        filial_id = self.request.query_params.get('pedi_fili')
        
        # NOVA LÓGICA: Filtro por ano atual por padrão
        # Se não há filtros específicos (nome ou número), mostrar apenas ano atual
        tem_filtros_especificos = cliente_nome or numero_orcamento
        
        if not tem_filtros_especificos:
            # Filtrar apenas orçamentos do ano atual para melhor performance
            ano_atual = datetime.now().year
            queryset = queryset.filter(pedi_data__year=ano_atual)
            logger.info(f"Aplicando filtro por ano atual: {ano_atual}")

        # Filtros mais específicos primeiro
        if empresa_id:
            queryset = queryset.filter(pedi_empr=empresa_id)
            
        if filial_id:
            queryset = queryset.filter(pedi_fili=filial_id)

        if numero_orcamento:
            try:
                numero = int(numero_orcamento)
                queryset = queryset.filter(pedi_nume=numero)
                logger.info(f"Buscando orçamento específico: {numero} (sem filtro de ano)")
            except ValueError:
                return queryset.none()

        # Filtro por nome do cliente (mais custoso, por último)
        if cliente_nome:
            logger.info(f"Buscando por nome do cliente: {cliente_nome} (sem filtro de ano)")
            # Cache para consultas de entidades
            cache_key = f"entidades_cliente_{cliente_nome}_{empresa_id}"
            entidades_ids = cache.get(cache_key)
            
            if entidades_ids is None:
                # Otimizar consulta de entidades
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_nome)
                    .filter(enti_empr=empresa_id if empresa_id else None)
                    .values_list('enti_clie', flat=True)[:100]  # Limitar resultados
                )
                # Cache por 5 minutos
                cache.set(cache_key, entidades_ids, 300)
            
            if entidades_ids:
                queryset = queryset.filter(pedi_forn__in=entidades_ids)
            else:
                return queryset.none()

        # Ordenar por número do orçamento (mais recentes primeiro)
        return queryset.order_by('-pedi_nume')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def list(self, request, *args, **kwargs):
        """Override do método list para implementar paginação e otimizações"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            banco = get_licenca_db_config(request)
            
            # Implementar paginação
            page = self.paginate_queryset(queryset)
            if page is not None:
                # Pré-carregar dados relacionados para evitar N+1 queries
                empresas_cache = {}
                entidades_cache = {}
                
                # Buscar empresas únicas
                empresas_ids = set(obj.pedi_empr for obj in page)
                empresas = Empresas.objects.using(banco).filter(empr_codi__in=empresas_ids)
                for empresa in empresas:
                    empresas_cache[empresa.empr_codi] = empresa.empr_nome
                
                # Buscar entidades únicas - corrigir estrutura do cache
                entidades_keys = set((obj.pedi_forn, obj.pedi_empr) for obj in page)
                entidades = Entidades.objects.using(banco).filter(
                    enti_clie__in=[forn for forn, empr in entidades_keys],
                    enti_empr__in=[empr for forn, empr in entidades_keys]
                )
                for entidade in entidades:
                    cache_key = f"{entidade.enti_clie}_{entidade.enti_empr}"
                    entidades_cache[cache_key] = entidade.enti_nome
                
                # Adicionar caches ao contexto do serializer
                context = self.get_serializer_context()
                context['empresas_cache'] = empresas_cache
                context['entidades_cache'] = entidades_cache
                
                serializer = self.get_serializer(page, many=True, context=context)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.list] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            logger.warning(f"[OrcamentoViewSet.create] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.create] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.retrieve] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except ValidationError as e:
            logger.warning(f"[OrcamentoViewSet.update] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.update] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            orcamento = self.get_object()
            banco = get_licenca_db_config(self.request)
            
            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")

            with transaction.atomic(using=banco):
                # Verificar se há itens associados
                itens_count = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=orcamento.pedi_empr,
                    iped_fili=orcamento.pedi_fili,
                    iped_pedi=str(orcamento.pedi_nume)
                ).count()
                
                if itens_count > 0:
                    # Excluir itens primeiro
                    ItensOrcamento.objects.using(banco).filter(
                        iped_empr=orcamento.pedi_empr,
                        iped_fili=orcamento.pedi_fili,
                        iped_pedi=str(orcamento.pedi_nume)
                    ).delete()
                    logger.info(f"Excluídos {itens_count} itens do orçamento {orcamento.pedi_nume}")
                
                # Excluir orçamento
                orcamento.delete()
                logger.info(f"🗑️ Exclusão Orçamento ID {orcamento.pedi_nume} concluída")

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.destroy] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='transformar-em-pedido')
    def transformar_em_pedido(self, request, pedi_nume=None, slug=None):
        """
        Transforma um orçamento em pedido de venda
        """
        try:
            orcamento = self.get_object()
            banco = get_licenca_db_config(request)
            
            if not banco:
                return Response(
                    {'erro': 'Banco de dados não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            with transaction.atomic(using=banco):
                # Obter próximo número de pedido
                ultimo_pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=orcamento.pedi_empr,
                    pedi_fili=orcamento.pedi_fili
                ).order_by('-pedi_nume').first()
                
                proximo_numero = (ultimo_pedido.pedi_nume + 1) if ultimo_pedido else 1
                
                # Verificar se o número já existe
                while PedidoVenda.objects.using(banco).filter(pedi_nume=proximo_numero).exists():
                    proximo_numero += 1
                
                # Criar pedido
                pedido = PedidoVenda.objects.using(banco).create(
                    pedi_empr=orcamento.pedi_empr,
                    pedi_fili=orcamento.pedi_fili,
                    pedi_nume=proximo_numero,
                    pedi_forn=orcamento.pedi_forn,
                    pedi_data=date.today(),
                    pedi_tota=orcamento.pedi_tota,
                    pedi_canc=False,
                    pedi_fina='0',  # À vista por padrão
                    pedi_vend=orcamento.pedi_vend or '0',
                    pedi_stat='0',  # Pendente
                    pedi_obse=orcamento.pedi_obse or ''
                )
                
                # Buscar itens do orçamento
                itens_orcamento = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=orcamento.pedi_empr,
                    iped_fili=orcamento.pedi_fili,
                    iped_pedi=str(orcamento.pedi_nume)
                )
                
                # Criar itens do pedido
                for item_orcamento in itens_orcamento:
                    Itenspedidovenda.objects.using(banco).create(
                        iped_empr=item_orcamento.iped_empr,
                        iped_fili=item_orcamento.iped_fili,
                        iped_pedi=str(pedido.pedi_nume),
                        iped_item=item_orcamento.iped_item,
                        iped_prod=item_orcamento.iped_prod,
                        iped_quan=item_orcamento.iped_quan,
                        iped_unit=item_orcamento.iped_unit,
                        iped_suto=item_orcamento.iped_unit,  # Subtotal = unit por padrão
                        iped_tota=item_orcamento.iped_tota,
                        iped_fret=0,  # Frete padrão
                        iped_desc=item_orcamento.iped_desc,
                        iped_unli=item_orcamento.iped_unli,
                        iped_forn=item_orcamento.iped_forn,
                        iped_vend=None,  # Vendedor será definido depois
                        iped_cust=0,  # Custo padrão
                        iped_tipo=None,  # Tipo padrão
                        iped_desc_item=False,  # Sem desconto por item por padrão
                        iped_perc_desc=item_orcamento.iped_pdes_item,  # Mapear corretamente
                        iped_unme=None,  # Unidade de medida padrão
                        # iped_data será definido automaticamente
                    )
                
                # Atualizar orçamento com número do pedido gerado
                orcamento.pedi_nume_pedi = pedido.pedi_nume
                orcamento.save(using=banco)
                
                logger.info(f"Orçamento {orcamento.pedi_nume} transformado em pedido {pedido.pedi_nume}")
                
                return Response({
                    'sucesso': True,
                    'mensagem': f'Orçamento {orcamento.pedi_nume} transformado em pedido {pedido.pedi_nume} com sucesso',
                    'numero_pedido': pedido.pedi_nume,
                    'orcamento_numero': orcamento.pedi_nume
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Erro ao transformar orçamento em pedido: {e}")
            return Response(
                {'error': f'Erro ao transformar orçamento em pedido: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

    @action(detail=False, methods=['get', 'patch'], url_path='parametros-desconto')
    def parametros_desconto(self, request, slug=None):
        """
        GET → retorna os parâmetros de desconto
        PATCH → atualiza os parâmetros de desconto
        """
        try:
            if request.method == 'GET':
                empresa_id = request.query_params.get('empresa_id') or request.query_params.get('empr')
                filial_id = request.query_params.get('filial_id') or request.query_params.get('fili')

                if not empresa_id or not filial_id:
                    return Response(
                        {'error': 'empresa_id/empr e filial_id/fili são obrigatórios'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                parametros = obter_parametros_pedidos(empresa_id, filial_id, request)

                # Função auxiliar para obter valor booleano do parâmetro
                def obter_valor_parametro(param_dict):
                    """Obtém o valor booleano do parâmetro, considerando tanto 'valor' quanto 'ativo'"""
                    if not param_dict.get('existe', False):
                        return False
                    
                    valor = param_dict.get('valor', False)
                    ativo = param_dict.get('ativo', False)
                    
                    # Se o parâmetro não está ativo no sistema, retorna False
                    if not ativo:
                        return False
                    
                    # Converter valor para boolean se necessário
                    if isinstance(valor, str):
                        return valor.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(valor, bool):
                        return valor
                    else:
                        return bool(valor)

                # Mapeamento correto: frontend_field → banco_field
                parametros_desconto = {
                    # Campos de desconto - mapeamento correto
                    'desconto_item_disponivel': obter_valor_parametro(parametros.get('desconto_item_pedido', {})),
                    'desconto_total_disponivel': obter_valor_parametro(parametros.get('desconto_total_disponivel', {})),
                    'desconto_item_orcamento': obter_valor_parametro(parametros.get('desconto_item_orcamento', {})),
                    'desconto_item_pedido': obter_valor_parametro(parametros.get('desconto_item_pedido', {})),
                    'desconto_total_pedido': obter_valor_parametro(parametros.get('desconto_total_pedido', {})),
                    'desconto_pedido': obter_valor_parametro(parametros.get('desconto_pedido', {})),
                    
                    # Campos adicionais que o frontend espera
                    'usar_preco_prazo': obter_valor_parametro(parametros.get('usar_preco_prazo', {})),
                    'usar_ultimo_preco': obter_valor_parametro(parametros.get('usar_ultimo_preco', {})),
                    'pedido_volta_estoque': obter_valor_parametro(parametros.get('pedido_volta_estoque', {})),
                    'validar_estoque_pedido': obter_valor_parametro(parametros.get('validar_estoque_pedido', {})),
                    'calcular_frete_automatico': obter_valor_parametro(parametros.get('calcular_frete_automatico', {})),
                }

                return Response(parametros_desconto, status=status.HTTP_200_OK)

            elif request.method == 'PATCH':
                empresa_id = request.data.get('empresa_id') or request.data.get('empr')
                filial_id = request.data.get('filial_id') or request.data.get('fili')

                if not empresa_id or not filial_id:
                    return Response(
                        {'error': 'empresa_id/empr e filial_id/fili são obrigatórios'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Mapear campos do frontend para os campos corretos do banco
                dados_mapeados = {}
                
                # Copiar todos os dados primeiro
                for key, value in request.data.items():
                    dados_mapeados[key] = value
                
                # Aplicar mapeamentos específicos
                if 'desconto_item_disponivel' in request.data:
                    dados_mapeados['desconto_item_pedido'] = request.data['desconto_item_disponivel']
                    # Remover o campo original para evitar confusão
                    dados_mapeados.pop('desconto_item_disponivel', None)
                
                # desconto_total_disponivel já tem o nome correto no banco
                
                sucesso = atualizar_parametros_pedidos(empresa_id, filial_id, dados_mapeados)
                if not sucesso:
                    return Response({'error': 'Erro ao atualizar'}, status=500)

                return Response({'success': True}, status=status.HTTP_200_OK)

            else:
                return Response({'error': 'Método não suportado'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        except Exception as e:
            logger.error(f"Erro geral nos parâmetros de desconto: {e}")
            return Response({'error': 'Erro interno'}, status=500)
