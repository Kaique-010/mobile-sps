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

from .models import PedidoVenda, Itenspedidovenda
from .serializers import PedidoVendaSerializer

from Entidades.models import Entidades
from Licencas.models import Empresas
from core.utils import get_licenca_db_config
from parametros_admin.decorators import parametros_pedidos_completo
from parametros_admin.integracao_pedidos import reverter_estoque_pedido, obter_status_estoque_pedido
from parametros_admin.utils_pedidos import obter_parametros_pedidos, atualizar_parametros_pedidos

logger = logging.getLogger('Pedidos')

class PedidoVendaViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoVendaSerializer
    lookup_field = 'pedi_nume'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['pedi_forn', 'pedi_nume']
    filterset_fields = ['pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_forn', 'pedi_data', 'pedi_stat']

    def get_object(self):
        """
        Sobrescreve get_object para lidar com registros duplicados
        """
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        lookup_value = self.kwargs[self.lookup_field]
        
        # Obter parâmetros adicionais para filtrar duplicatas
        pedi_empr = self.request.query_params.get('pedi_empr')
        pedi_fili = self.request.query_params.get('pedi_fili')
        
        queryset = self.get_queryset()
        
        # Filtrar por empresa e filial se fornecidos
        if pedi_empr:
            queryset = queryset.filter(pedi_empr=pedi_empr)
        if pedi_fili:
            queryset = queryset.filter(pedi_fili=pedi_fili)
            
        # Filtrar pelo lookup_field
        queryset = queryset.filter(**{self.lookup_field: lookup_value})
        
        # Retornar o primeiro resultado para evitar erro de múltiplos objetos
        obj = queryset.first()
        
        if not obj:
            raise NotFound("Pedido não encontrado.")
            
        # Verificar permissões
        self.check_object_permissions(self.request, obj)
        
        return obj
    
    def get_queryset(self):
        from datetime import datetime
        
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
            
        # Base queryset otimizada COM PREFETCH DOS ITENS
        queryset = PedidoVenda.objects.using(banco).prefetch_related(
            Prefetch(
                'itenspedidovenda_set',
                queryset=Itenspedidovenda.objects.using(banco).all()
            )
        )
        
        # Obter parâmetros de filtro
        cliente_nome = self.request.query_params.get('cliente_nome')
        numero_pedido = self.request.query_params.get('pedi_nume')
        empresa_id = self.request.query_params.get('pedi_empr')
        filial_id = self.request.query_params.get('pedi_fili')
        
        # NOVA LÓGICA: Filtro por ano atual por padrão
        # Se não há filtros específicos (nome ou número), mostrar apenas ano atual
        tem_filtros_especificos = cliente_nome or numero_pedido
        
        if not tem_filtros_especificos:
            # Filtrar apenas pedidos do ano atual para melhor performance
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
        print(f"🎯 [VIEW] Recebendo requisição de criação de pedido")
        print(f"🎯 [VIEW] Dados da requisição: {request.data}")
        
        try:
            logger.info(f"[PedidoVendaViewSet.create] request.data: {request.data}")
        except Exception as e:
            logger.error(f"Erro ao acessar request.data: {e}")

        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        try:
            serializer.is_valid(raise_exception=True)
            print(f"🎯 [VIEW] Dados validados com sucesso, criando pedido...")
            self.perform_create(serializer)
            print(f"🎯 [VIEW] Pedido criado com sucesso")
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            print(f"❌ [VIEW] Erro de validação: {e.detail}")
            logger.warning(f"[PedidoVendaViewSet.create] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[PedidoVendaViewSet.create] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @parametros_pedidos_completo
    def update(self, request, *args, **kwargs):
        print(f"🎯 [VIEW] Recebendo requisição de atualização de pedido")
        print(f"🎯 [VIEW] Dados da requisição: {request.data}")
        
        try:
            instance = self.get_object()
            print(f"🎯 [VIEW] Atualizando pedido {instance.pedi_nume}")
            
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            print(f"🎯 [VIEW] Dados validados com sucesso, atualizando pedido...")
            pedido = serializer.save()
            print(f"🎯 [VIEW] Pedido atualizado com sucesso")
            return Response(self.get_serializer(pedido).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            logger.warning(f"[PedidoVendaViewSet.update] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[PedidoVendaViewSet.update] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        try:
            pedido = self.get_object()
            banco = get_licenca_db_config(self.request)
            
            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")

            # Reverter estoque antes de excluir
            try:
                resultado_estoque = reverter_estoque_pedido(pedido, request)
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
    def cancelar_pedido(self, request, pedi_nume=None):
        """
        Cancela um pedido e reverte o estoque se configurado
        """
        try:
            pedido = self.get_object()
            banco = get_licenca_db_config(request)
            
            if not banco:
                return Response(
                    {'erro': 'Banco de dados não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verificar se pedido já está cancelado
            if pedido.pedi_stat == '4':  # Cancelado
                return Response(
                    {'erro': 'Pedido já está cancelado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic(using=banco):
                # Reverter estoque
                resultado_estoque = reverter_estoque_pedido(pedido, request)
                
                # Atualizar status do pedido
                pedido.pedi_stat = '4'  # Cancelado
                pedido.pedi_canc = True
                pedido.save(using=banco)
                
                logger.info(f"Pedido {pedido.pedi_nume} cancelado")
                
                return Response({
                    'sucesso': True,
                    'mensagem': f'Pedido {pedido.pedi_nume} cancelado com sucesso',
                    'estoque_revertido': resultado_estoque
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Erro ao cancelar pedido: {e}")
            return Response(
                {'erro': 'Erro interno ao cancelar pedido'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        
