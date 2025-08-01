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
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
            
        # Base queryset otimizada
        queryset = PedidoVenda.objects.using(banco).all()
        
        # Aplicar filtros de forma otimizada
        cliente_nome = self.request.query_params.get('cliente_nome')
        numero_pedido = self.request.query_params.get('pedi_nume')
        empresa_id = self.request.query_params.get('pedi_empr')
        filial_id = self.request.query_params.get('pedi_fili')

        # Filtros mais específicos primeiro
        if empresa_id:
            queryset = queryset.filter(pedi_empr=empresa_id)
            
        if filial_id:
            queryset = queryset.filter(pedi_fili=filial_id)

        if numero_pedido:
            try:
                numero = int(numero_pedido)
                queryset = queryset.filter(pedi_nume=numero)
            except ValueError:
                return queryset.none()

        # Filtro por nome do cliente (mais custoso, por último)
        if cliente_nome:
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
        return queryset.order_by('-pedi_nume')
    
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
    
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