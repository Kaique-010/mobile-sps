import logging
from django.db import transaction
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from .models import PedidoVenda, Itenspedidovenda
from .serializers import PedidoVendaSerializer
from core.mixins.vendedor_mixin import VendedorEntidadeMixin
from Entidades.models import Entidades
from Licencas.models import Empresas
from core.utils import get_licenca_db_config
from rest_framework.permissions import IsAuthenticated
from parametros_admin.decorators import parametros_pedidos_completo
from parametros_admin.utils_pedidos import obter_parametros_pedidos, atualizar_parametros_pedidos
from ParametrosSps.services.pedidos_service import PedidosService

logger = logging.getLogger('Pedidos')

class PedidoVendaViewSet(viewsets.ModelViewSet, VendedorEntidadeMixin):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Pedidos'
    serializer_class = PedidoVendaSerializer
    lookup_field = 'pedi_nume'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['pedi_forn', 'pedi_nume']
    filterset_fields = ['pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_forn', 'pedi_data', 'pedi_stat']

    def get_object(self):
        """
        Obtém o objeto pedido usando chave composta empresa/filial/numero
        """
        try:
            # Priorizar parâmetros da URL (self.kwargs) primeiro
            empresa = self.kwargs.get('empresa') or self.kwargs.get('pedi_empr')
            filial = self.kwargs.get('filial') or self.kwargs.get('pedi_fili') 
            numero = self.kwargs.get('numero') or self.kwargs.get('pedi_nume')
            
            # Se não encontrou na URL, tentar query_params como fallback
            if not empresa:
                empresa = self.request.query_params.get('empresa') or self.request.query_params.get('pedi_empr')
            if not filial:
                filial = self.request.query_params.get('filial') or self.request.query_params.get('pedi_fili')
            if not numero:
                numero = self.request.query_params.get('numero') or self.request.query_params.get('pedi_nume')
                
            # Se ainda não encontrou, tentar request.data como último recurso
            if not empresa and hasattr(self.request, 'data'):
                empresa = self.request.data.get('empresa') or self.request.data.get('pedi_empr')
            if not filial and hasattr(self.request, 'data'):
                filial = self.request.data.get('filial') or self.request.data.get('pedi_fili')
            if not numero and hasattr(self.request, 'data'):
                numero = self.request.data.get('numero') or self.request.data.get('pedi_nume')
            
            logger.debug(f"Parâmetros recebidos - Empresa: {empresa}, Filial: {filial}, Numero: {numero}")
            
            if not all([empresa, filial, numero]):
                raise ValidationError("Empresa, filial e número são obrigatórios")
            
            banco = get_licenca_db_config(self.request)
            pedido = get_object_or_404(
                PedidoVenda.objects.using(banco),
                pedi_empr=empresa,
                pedi_fili=filial,
                pedi_nume=numero
            )
            
            return pedido
            
        except PedidoVenda.DoesNotExist:
            raise NotFound("Pedido não encontrado")
        except Exception as e:
            logger.error(f"Erro ao buscar pedido: {e}")
            raise ValidationError(f"Erro ao buscar pedido: {str(e)}")
    
    def get_queryset(self):
        from datetime import datetime
        
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
            
        # Remover o prefetch_related problemático
        queryset = PedidoVenda.objects.using(banco)
        queryset = self.filter_por_vendedor(queryset, 'pedi_vend')
        
        # Obter parâmetros de filtro
        cliente_nome = self.request.query_params.get('cliente_nome')
        numero_pedido = self.request.query_params.get('pedi_nume')
        empresa_id = self.request.query_params.get('pedi_empr')
        filial_id = self.request.query_params.get('pedi_fili')
        
        # NOVA LÓGICA: Filtro por ano atual por padrão
        tem_filtros_especificos = cliente_nome or numero_pedido
        
        if not tem_filtros_especificos:
            ano_atual = datetime.now().year
            queryset = queryset.filter(pedi_data__year=ano_atual)
            logger.info(f"Aplicando filtro por ano atual: {ano_atual}")

        # Filtros mais específicos primeiro
        if empresa_id:
            queryset = queryset.filter(pedi_empr=empresa_id)
            
        if filial_id:
            queryset = queryset.filter(pedi_fili=filial_id)

        if numero_pedido:
            try:
                numero = int(numero_pedido)
                queryset = queryset.filter(pedi_nume=numero)
                logger.info(f"Buscando pedido específico: {numero} (sem filtro de ano)")
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

        # Ordenar por número do pedido (mais recentes primeiro)
        print(f"nome do cliente: {cliente_nome}")

        return queryset.order_by('-pedi_nume')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def list(self, request, *args, **kwargs):
        """
        Override do método list para otimizar performance com muitos registros
        """
        try:
            banco = get_licenca_db_config(request)
            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")

            # Obter queryset filtrado
            queryset = self.filter_queryset(self.get_queryset())
            
            # Aplicar paginação
            page = self.paginate_queryset(queryset)
            if page is not None:
                # Pré-carregar dados relacionados para evitar N+1 queries
                empresas_ids = list(set([p.pedi_empr for p in page]))
                fornecedores_ids = list(set([p.pedi_forn for p in page]))
                
                # Cache de empresas
                empresas_cache = {}
                if empresas_ids:
                    empresas = Empresas.objects.using(banco).filter(empr_codi__in=empresas_ids)
                    empresas_cache = {emp.empr_codi: emp.empr_nome for emp in empresas}
                
                # Cache de entidades (clientes) - corrigir estrutura
                entidades_cache = {}
                if fornecedores_ids and empresas_ids:
                    entidades = Entidades.objects.using(banco).filter(
                        enti_clie__in=fornecedores_ids,
                        enti_empr__in=empresas_ids
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
            logger.error(f"Erro no método list: {e}")
            return Response(
                {'erro': 'Erro interno do servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @parametros_pedidos_completo
    def create(self, request, *args, **kwargs):
        """
        Cria um pedido e realiza baixa automática de estoque conforme parâmetros.
        """
        logger.info(f"🎯 [CREATE] Iniciando criação de pedido")
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        
        try:
            serializer.is_valid(raise_exception=True)
            pedido = serializer.save()
            logger.info(f"✅ Pedido {pedido.pedi_nume} criado com sucesso")

            # ↓ BAIXA DE ESTOQUE JÁ É FEITA AUTOMATICAMENTE NO SERIALIZER
            # Não precisa fazer aqui para evitar duplicação

            headers = self.get_success_headers(serializer.data)
            return Response(
                {'pedido': serializer.data},
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except ValidationError as e:
            logger.warning(f"❌ Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"💥 Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # @parametros_pedidos_completo  # Comentado temporariamente devido ao erro de permissão
    def retrieve(self, request, *args, **kwargs):
        """
        Recupera um pedido específico
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Erro ao recuperar pedido: {e}")
            return Response(
                {'erro': 'Erro interno do servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """
        Atualiza pedido. Controla movimentação de estoque apenas nas diferenças de itens.
        """
        logger.info(f"[UPDATE] Iniciando atualização de pedido com controle de estoque diferencial")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        banco = get_licenca_db_config(request)

        # Snapshot antes da atualização
        itens_antes = {
            (i.iped_prod): i.iped_quan
            for i in instance.itens.all().using(banco)
        }

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        pedido = serializer.save()

        # Snapshot depois da atualização
        itens_depois = {
            (i.iped_prod): i.iped_quan
            for i in pedido.itens.all().using(banco)
        }

        # Calcula diferenças
        novos = set(itens_depois.keys()) - set(itens_antes.keys())
        removidos = set(itens_antes.keys()) - set(itens_depois.keys())
        alterados = {
            k for k in itens_depois.keys() & itens_antes.keys()
            if itens_depois[k] != itens_antes[k]
        }

        # ↓ Processa só diferenças
        try:
            for prod_id in novos:
                item = pedido.itens.using(banco).filter(iped_prod=prod_id).first()
                PedidosService._baixar_item(pedido, item, banco)

            for prod_id in removidos:
                quantidade = itens_antes[prod_id]
                fake_item = type('obj', (), {'iped_prod': prod_id, 'iped_quan': quantidade})
                PedidosService._estornar_item(pedido, fake_item, banco)

            for prod_id in alterados:
                diferenca = itens_depois[prod_id] - itens_antes[prod_id]
                item = pedido.itens.using(banco).filter(iped_prod=prod_id).first()
                if diferenca > 0:
                    # aumentou a quantidade → baixa diferença
                    item.iped_quan = diferenca
                    PedidosService._baixar_item(pedido, item, banco)
                elif diferenca < 0:
                    # reduziu quantidade → devolve diferença
                    item.iped_quan = abs(diferenca)
                    PedidosService._estornar_item(pedido, item, banco)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[UPDATE] Erro ao ajustar estoque: {e}")
            return Response({'error': 'Erro ao ajustar estoque'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    
    def destroy(self, request, *args, **kwargs):
        try:
            pedido = self.get_object()
            banco = get_licenca_db_config(self.request)
            
            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")

            # Reverter estoque antes de excluir
            try:
                resultado_estoque = PedidosService.estornar_estoque_pedido(pedido, request)
                if not resultado_estoque.get('sucesso', True):
                    logger.warning(f"Erro ao reverter estoque: {resultado_estoque.get('erro')}")
                elif resultado_estoque.get('processado'):
                    logger.info(f"Estoque revertido para pedido {pedido.pedi_nume}")
            except Exception as e:
                logger.error(f"Erro ao reverter estoque: {e}")

            with transaction.atomic(using=banco):
                # Excluir itens do pedido - corrigindo o filtro
                Itenspedidovenda.objects.using(banco).filter(
                    iped_empr=pedido.pedi_empr,
                    iped_fili=pedido.pedi_fili,
                    iped_pedi=str(pedido.pedi_nume)  # Convertendo para string
                ).delete()
                
                # Excluir pedido
                pedido.delete()
                logger.info(f"🗑️ Exclusão Pedido ID {pedido.pedi_nume} concluída")

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"[PedidoVendaViewSet.destroy] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def cancelar_pedido(self, request, empresa=None, filial=None, numero=None, **kwargs):
        """
        Cancela um pedido e reverte o estoque, se o parâmetro de cancelamento estiver habilitado.
        """
        try:
            pedido = self.get_object()
            banco = get_licenca_db_config(request)
           

            if not banco:
                return Response({'erro': 'Banco de dados não encontrado'}, status=status.HTTP_404_NOT_FOUND)

            # 🔹 Verifica parâmetro
            if not PedidosService.pedido_cancela_nao_exclui(banco, pedido.pedi_empr):
                return Response(
                    {'erro': 'Cancelamento de pedido não está habilitado nos parâmetros.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if pedido.pedi_stat == '4':  # já cancelado
                return Response({'erro': 'Pedido já cancelado'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic(using=banco):
                # 🔹 Reverte estoque se configurado
                resultado_estoque = PedidosService.estornar_estoque_pedido(pedido, request)
                logger.info(f"♻️ Estoque revertido para pedido {pedido.pedi_nume}: {resultado_estoque}")

                # 🔹 Atualiza status do pedido
                pedido.pedi_stat = '4'  # Cancelado
                pedido.pedi_canc = True
                pedido.save(using=banco, update_fields=['pedi_stat', 'pedi_canc'])

                return Response({
                    'sucesso': True,
                    'mensagem': f'Pedido {pedido.pedi_nume} cancelado e estoque revertido',
                    'estoque': resultado_estoque
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Erro ao cancelar pedido: {e}")
            return Response({'erro': 'Erro interno ao cancelar pedido'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    
    @action(detail=True, methods=['get'])
    def status_estoque(self, request, pedi_nume=None):
        """
        Obtém status do estoque relacionado ao pedido
        """
        try:
            pedido = self.get_object()
            
            status_estoque = obter_status_estoque_pedido(
                pedido.pedi_nume,
                pedido.pedi_empr,
                pedido.pedi_fili,
                request
            )
            
            return Response(status_estoque, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erro ao obter status do estoque: {e}")
            return Response(
                {'erro': 'Erro ao obter status do estoque'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get', 'patch'], url_path='parametros-desconto')
    def parametros_desconto(self, request, slug=None):
        """
        GET → retorna os parâmetros de desconto para pedidos
        PATCH → atualiza os parâmetros de desconto para pedidos
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

                parametros_desconto = {
                    'desconto_item_disponivel': parametros.get('desconto_item_pedido', {}).get('valor', False),
                    'desconto_total_disponivel': parametros.get('desconto_total_disponivel', {}).get('valor', False),
                    'desconto_maximo_item': parametros.get('desconto_maximo_item', {}).get('valor', 50),
                    'desconto_maximo_total': parametros.get('desconto_maximo_total', {}).get('valor', 30),
                }

                return Response(parametros_desconto, status=status.HTTP_200_OK)

            elif request.method == 'PATCH':
                empresa_id = request.data.get('empresa_id') or request.data.get('empr')
                filial_id = request.data.get('filial_id') or request.data.get('fili')

                logger.info(f"[PATCH parametros_desconto] Recebendo dados: {request.data}")
                logger.info(f"[PATCH parametros_desconto] empresa_id: {empresa_id}, filial_id: {filial_id}")

                if not empresa_id or not filial_id:
                    return Response(
                        {'error': 'empresa_id/empr e filial_id/fili são obrigatórios'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Mapear parâmetros do frontend para os nomes corretos no banco
                dados_mapeados = {}
                
                # Mapear desconto_item_disponivel para desconto_item_pedido
                if 'desconto_item_disponivel' in request.data:
                    dados_mapeados['desconto_item_pedido'] = request.data['desconto_item_disponivel']
                
                # Os outros parâmetros mantêm o mesmo nome
                for param in ['desconto_total_disponivel', 'desconto_maximo_item', 'desconto_maximo_total']:
                    if param in request.data:
                        dados_mapeados[param] = request.data[param]
                
                logger.info(f"[PATCH parametros_desconto] Dados originais: {request.data}")
                logger.info(f"[PATCH parametros_desconto] Dados mapeados: {dados_mapeados}")
                
                # Atualizar parâmetros no banco
                logger.info(f"[PATCH parametros_desconto] Chamando atualizar_parametros_pedidos...")
                sucesso = atualizar_parametros_pedidos(empresa_id, filial_id, dados_mapeados)
                logger.info(f"[PATCH parametros_desconto] Resultado da atualização: {sucesso}")
                
                if not sucesso:
                    return Response({'error': 'Erro ao atualizar parâmetros'}, status=500)

                return Response({'success': True}, status=status.HTTP_200_OK)

            else:
                return Response({'error': 'Método não suportado'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        except Exception as e:
            logger.error(f"Erro geral nos parâmetros de desconto: {e}")
            return Response({'error': 'Erro interno'}, status=500)
        
