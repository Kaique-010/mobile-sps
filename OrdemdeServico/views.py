from rest_framework.viewsets import ModelViewSet
from rest_framework import status, filters
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction, IntegrityError
from django.db.models import Max
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from django.http import HttpResponse
from OrdemdeServico.utils import get_next_item_number_sequence, get_next_service_id, get_next_image_id
from listacasamento.utils import get_next_item_number
from .permissions import PodeVerOrdemDoSetor, OrdemServicoPermission, WorkflowPermission
from .models import (
    Ordemservico, Ordemservicopecas, Ordemservicoservicos,
    Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois, 
    WorkflowSetor, HistoricoWorkflow, OrdemServicoFaseSetor
)
from .serializers import (
    OrdemServicoSerializer, OrdemServicoPecasSerializer, OrdemServicoServicosSerializer,
    ImagemAntesSerializer, ImagemDuranteSerializer, ImagemDepoisSerializer, 
    WorkflowSetorSerializer, OrdemServicoFaseSetorSerializer
)
from .serializers_historico import HistoricoWorkflowSerializer
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.decorator import modulo_necessario, ModuloRequeridoMixin

import logging
logger = logging.getLogger(__name__)


class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, OrdemServicoPermission, PodeVerOrdemDoSetor]

    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error(f"Banco de dados não encontrado para {self.__class__.__name__}")
            raise NotFound("Banco de dados não encontrado.")
        return banco

    def get_queryset(self):
        return super().get_queryset().using(self.get_banco())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    @transaction.atomic(using='default')
    def create(self, request, *args, **kwargs):
        try:
            banco = self.get_banco()
            # Evita múltiplos acessos ao request.data
            data = getattr(request, '_cached_data', None)
            if data is None:
                data = request.data
                request._cached_data = data
            
            is_many = isinstance(data, list)
            serializer = self.get_serializer(data=data, many=is_many)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic(using=banco):
                serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            # Captura erros de validação sem acessar request.data novamente
            logger.error(f"Erro de validação: {ve}")
            raise
        except Exception as e:
            logger.error(f"Erro ao processar requisição: {str(e)}")
            raise

    def update(self, request, *args, **kwargs):
        banco = self.get_banco()
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data)


class OrdemServicoFaseSetorViewSet(BaseMultiDBModelViewSet):
    """ViewSet para consultar fases de setores (somente leitura)"""
    modulo_necessario = 'OrdemdeServico'
    queryset = OrdemServicoFaseSetor.objects.all()
    serializer_class = OrdemServicoFaseSetorSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['osfs_codi', 'osfs_nome']
    ordering_fields = ['osfs_codi', 'osfs_nome']
    search_fields = ['osfs_nome']
    http_method_names = ['get']  # Apenas consulta (tabela não gerenciada)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context


class HistoricoWorkflowViewSet(BaseMultiDBModelViewSet):
    """ViewSet para consultar histórico de movimentações entre setores"""
    modulo_necessario = 'OrdemdeServico'
    serializer_class = HistoricoWorkflowSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['hist_empr', 'hist_fili', 'hist_orde', 'hist_seto_orig', 'hist_seto_dest', 'hist_usua']
    ordering_fields = ['hist_data', 'hist_orde']
    search_fields = ['hist_orde']
    http_method_names = ['get', 'post']  # Apenas consulta e criação

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context


class WorkflowSetorViewSet(BaseMultiDBModelViewSet):
    """ViewSet para gerenciar configurações de workflow entre setores"""
    modulo_necessario = 'OrdemdeServico'
    queryset = WorkflowSetor.objects.all()
    serializer_class = WorkflowSetorSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['wkfl_seto_orig', 'wkfl_seto_dest', 'wkfl_ativo']
    ordering_fields = ['wkfl_orde', 'wkfl_seto_orig', 'wkfl_seto_dest']
    search_fields = ['wkfl_seto_orig', 'wkfl_seto_dest']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context


class OrdemServicoViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = OrdemServicoSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['orde_stat_orde', 'orde_prio', 'orde_tipo', 'orde_enti']
    ordering_fields = ['orde_data_aber', 'orde_data_fech', 'orde_prio']
    search_fields = ['orde_prob', 'orde_defe_desc', 'orde_obse']
    permission_classes = [IsAuthenticated, OrdemServicoPermission, PodeVerOrdemDoSetor]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self):
        banco = self.get_banco()
        user_setor = self.request.user.setor
        qs = Ordemservico.objects.using(banco)
        if user_setor and hasattr(user_setor, 'osfs_codi') and user_setor.osfs_codi is not None:
            qs = qs.filter(orde_seto=user_setor.osfs_codi)
        return qs.order_by('orde_nume', 'orde_data_aber')

    def get_next_ordem_numero(self, empre, fili):
        banco = self.get_banco()
        ultimo = Ordemservico.objects.using(banco).filter(orde_empr=empre, orde_fili=fili).aggregate(Max('orde_nume'))['orde_nume__max']
        return (ultimo or 0) + 1

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()

        data['orde_stat_orde'] = 0
        if request.user and request.user.pk:
            data['orde_usua_aber'] = request.user.pk

        empre = data.get('orde_empr') or data.get('empr')
        fili = data.get('orde_fili') or data.get('fili')
        if not empre or not fili:
            return Response({"detail": "Empresa e Filial são obrigatórios."}, status=400)

        data['orde_nume'] = self.get_next_ordem_numero(empre, fili)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            instance = serializer.save()
        logger.info(f"O.S. {instance.orde_nume} aberta por user {request.user.pk if request.user else 'anon'}")
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(
        detail=True, 
        methods=['post'],
        permission_classes=[IsAuthenticated, OrdemServicoPermission, PodeVerOrdemDoSetor, WorkflowPermission],
    )
    def atualizar_total(self, request, pk=None, slug=None):
        """
        Endpoint para atualizar o total da ordem de serviço.
        """
        try:
            banco = self.get_banco()
            ordem = self.get_object()
            
            with transaction.atomic(using=banco):
                ordem.calcular_total()
                ordem.save(using=banco)
            
            serializer = self.get_serializer(ordem)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao atualizar total da ordem {pk}: {str(e)}")
            return Response(
                {"error": "Erro ao atualizar total da ordem de serviço"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, PodeVerOrdemDoSetor, WorkflowPermission],
        url_path='avancar-setor'
    )
    def avancar_setor(self, request, pk=None, slug=None):
        """
        Endpoint para avançar ordem para próximo setor do workflow.
        """
        try:
            banco = self.get_banco()
            ordem = self.get_object()
            setor_destino = request.data.get('setor_destino')
            
            if not setor_destino:
                return Response(
                    {"error": "setor_destino é obrigatório"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic(using=banco):
                sucesso = ordem.avancar_setor(setor_destino, request.user, banco)
                
                if not sucesso:
                    return Response(
                        {"error": "Não é possível avançar para este setor"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            serializer = self.get_serializer(ordem)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao avançar setor da ordem {pk}: {str(e)}")
            return Response(
                {"error": "Erro ao avançar setor da ordem"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated, PodeVerOrdemDoSetor, WorkflowPermission],
        url_path='proximos-setores'
    )
    def proximos_setores(self, request, pk=None, slug=None):
        """
        Endpoint para obter próximos setores disponíveis para avançar.
        Retorna múltiplas opções quando existem setores com a mesma ordem.
        """
        try:
            banco = self.get_banco()
            logger.info(f"Banco obtido: {banco}")
            
            ordem = self.get_object()
            logger.info(f"Ordem obtida: {ordem.orde_nume}, setor atual: {ordem.orde_seto}")
            
            setores = ordem.obter_proximos_setores(banco)
            logger.info(f"Setores encontrados: {list(setores)}")
            
            return Response({
                "proximos_setores": [
                    {
                        "codigo": setor.wkfl_seto_dest, 
                        "nome": f"Setor {setor.wkfl_seto_dest}",
                        "ordem": setor.wkfl_orde
                    }
                    for setor in setores
                ]
            })
            
        except Exception as e:
            import traceback
            logger.error(f"Erro ao obter próximos setores da ordem {pk}: {str(e)}")
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            return Response(
                {"error": f"Erro ao obter próximos setores: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='historico-workflow'
    )
    def historico_workflow(self, request, pk=None, slug=None):
        """
        Endpoint para obter histórico de movimentação entre setores.
        """
        try:
            banco = self.get_banco()
            ordem = self.get_object()
            
            historico = ordem.obter_historico_workflow(banco)
            
            return Response({
                "historico": [
                    {
                        "setor_origem": h.hist_seto_orig,
                        "setor_destino": h.hist_seto_dest,
                        "usuario": h.hist_usua,
                        "data": h.hist_data,
                        "observacao": h.hist_observacao
                    }
                    for h in historico
                ]
            })
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico workflow da ordem {pk}: {str(e)}")
            return Response(
                {"error": "Erro ao obter histórico de workflow"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class OrdemServicoPecasViewSet(BaseMultiDBModelViewSet,ModelViewSet):
    serializer_class = OrdemServicoPecasSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
   
    def atualizar_total_ordem(self, peca_empr, peca_fili, peca_orde):
        banco = self.get_banco()
        try:
            ordem = Ordemservico.objects.using(banco).get(
                orde_empr=peca_empr,
                orde_fili=peca_fili,
                orde_nume=peca_orde
            )
            ordem.calcular_total()
            ordem.save(using=banco)
        except Ordemservico.DoesNotExist:
            logger.error(f"Ordem de serviço não encontrada: {peca_orde}")

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        peca_empr = self.request.query_params.get('peca_empr')
        peca_fili = self.request.query_params.get('peca_fili')
        peca_orde = self.request.query_params.get('peca_orde')

        if not all([peca_empr, peca_fili, peca_orde]):
            logger.warning("Parâmetros obrigatórios não fornecidos (peca_empr, peca_fili, peca_orde)")
            return Ordemservicopecas.objects.none()

        queryset = Ordemservicopecas.objects.using(banco).filter(
            peca_empr=peca_empr,
            peca_fili=peca_fili,
            peca_orde=peca_orde
        )

        logger.info(f"Parâmetros recebidos: peca_empr={peca_empr}, peca_fili={peca_fili}, peca_orde={peca_orde}")
        logger.info(f"Queryset filtrado: {queryset.query}")
        return queryset.order_by('peca_id')

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        peca_id = self.kwargs.get('pk')
        peca_orde = self.request.query_params.get("peca_orde")
        peca_empr = self.request.query_params.get("peca_empr")
        peca_fili = self.request.query_params.get("peca_fili")

        if not all([peca_orde, peca_empr, peca_fili, peca_id]):
            raise ValidationError("Parâmetros peca_orde, peca_empr, peca_fili e pk (peca_id) são obrigatórios.")

        try:
            return self.get_queryset().get(
                peca_id=peca_id,
                peca_orde=peca_orde,
                peca_empr=peca_empr,
                peca_fili=peca_fili
            )
        except Ordemservicopecas.DoesNotExist:
            raise NotFound("peca não encontrado na lista especificada.")
        except Ordemservicopecas.MultipleObjectsReturned:
            raise ValidationError("Mais de um peca encontrado com essa chave composta.")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def destroy(self, request, *args, **kwargs):
        peca = self.get_object()
        if peca.peca_pedi != 0:
            return Response({"detail": "Não é possível excluir peca já associado a pedido."}, status=400)
        return super().destroy(request, *args, **kwargs)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            logger.info(f"Criação de peca(s) por {request.user.pk if request.user else 'None'}")

            if isinstance(request.data, list):
                serializer = self.get_serializer(data=request.data, many=True)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return super().create(request, *args, **kwargs)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response({'detail': 'Erro de integridade.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
  
  
  
    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=404)

        data = request.data
        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):
                # Validar e adicionar novos itens
                for item in adicionar:
                    # Validar campos obrigatórios
                    campos_obrigatorios = ['peca_orde', 'peca_empr', 'peca_fili', 'peca_codi']
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

                    # Converter campos numéricos
                    try:
                        item['peca_orde'] = int(item['peca_orde'])
                        item['peca_empr'] = int(item['peca_empr'])
                        item['peca_fili'] = int(item['peca_fili'])
                        item['peca_quan'] = float(item.get('peca_quan', 0))
                        item['peca_unit'] = float(item.get('peca_unit', 0))
                        item['peca_tota'] = float(item.get('peca_tota', 0))
                    except (ValueError, TypeError) as e:
                        raise ValidationError({
                            'error': f"Erro ao converter valores numéricos: {str(e)}",
                            'item': item
                        })

                    item['peca_id'] = get_next_item_number_sequence(
                        banco, item['peca_orde'], item['peca_empr'], item['peca_fili']
                    )
                    serializer = OrdemServicoPecasSerializer(data=item, context={'banco': banco})
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save()

                    obj_refetch = Ordemservicopecas.objects.using(banco).get(
                        peca_empr=obj.peca_empr,
                        peca_fili=obj.peca_fili,
                        peca_orde=obj.peca_orde,
                        peca_id=obj.peca_id,
                    )
                    resposta['adicionados'].append(
                        OrdemServicoPecasSerializer(obj_refetch, context={'banco': banco}).data
                    )

                # Validar e editar itens existentes
                for item in editar:
                    if not all(k in item for k in ['peca_id', 'peca_orde', 'peca_empr', 'peca_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para edição",
                            'item': item
                        })

                    try:
                        obj = Ordemservicopecas.objects.using(banco).get(
                            peca_id=item['peca_id'],
                            peca_orde=item['peca_orde'],
                            peca_empr=item['peca_empr'],
                            peca_fili=item['peca_fili']
                        )
                    except Ordemservicopecas.DoesNotExist:
                        logger.warning(f"Peça não encontrada para edição: {item}")
                        continue

                    serializer = OrdemServicoPecasSerializer(obj, data=item, context={'banco': banco}, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    resposta['editados'].append(serializer.data)

                # Validar e remover itens
                for item in remover:
                    if not all(k in item for k in ['peca_id', 'peca_orde', 'peca_empr', 'peca_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para remoção",
                            'item': item
                        })

                    Ordemservicopecas.objects.using(banco).filter(
                        peca_id=item['peca_id'],
                        peca_orde=item['peca_orde'],
                        peca_empr=item['peca_empr'],
                        peca_fili=item['peca_fili']
                    ).delete()
                    resposta['removidos'].append(item['peca_id'])

            return Response(resposta)

        except ValidationError as e:
            logger.error(f"Erro de validação ao processar update_lista: {str(e)}")
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(f"Erro ao processar update_lista: {str(e)}")
            return Response({"error": str(e)}, status=400)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:  # Se criou com sucesso
            data = request.data
            self.atualizar_total_ordem(
                data.get('peca_empr'),
                data.get('peca_fili'),
                data.get('peca_orde')
            )
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:  # Se atualizou com sucesso
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.peca_empr,
                instance.peca_fili,
                instance.peca_orde
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.peca_empr, instance.peca_fili, instance.peca_orde
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:  # Se deletou com sucesso
            self.atualizar_total_ordem(empr, fili, orde)
        return response


class OrdemServicoServicosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = OrdemServicoServicosSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def atualizar_total_ordem(self, serv_empr, serv_fili, serv_orde):
        banco = self.get_banco()
        try:
            ordem = Ordemservico.objects.using(banco).get(
                orde_empr=serv_empr,
                orde_fili=serv_fili,
                orde_nume=serv_orde
            )
            ordem.calcular_total()
            ordem.save(using=banco)
        except Ordemservico.DoesNotExist:
            logger.error(f"Ordem de serviço não encontrada: {serv_orde}")

    def get_queryset(self):
        banco = self.get_banco()
        serv_empr = self.request.query_params.get('serv_empr') or self.request.query_params.get('empr')
        serv_fili = self.request.query_params.get('serv_fili') or self.request.query_params.get('fili')
        serv_orde = self.request.query_params.get('serv_orde') or self.request.query_params.get('ordem')

        if not all([serv_empr, serv_fili, serv_orde]):
            logger.warning("Parâmetros obrigatórios não fornecidos (serv_empr/empr, serv_fili/fili, serv_orde/ordem)")
            return Ordemservicoservicos.objects.using(banco).none()

        qs = Ordemservicoservicos.objects.using(banco).filter(
            serv_empr=serv_empr,
            serv_fili=serv_fili,
            serv_orde=serv_orde
        )
        
        logger.info(f"Filtrando serviços com: ordem={serv_orde}, empresa={serv_empr}, filial={serv_fili}")
        return qs.order_by('serv_sequ')

    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = self.get_banco()
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=404)

        data = request.data
        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):
                # Validar e adicionar novos itens
                for item in adicionar:
                    # Validar campos obrigatórios
                    campos_obrigatorios = ['serv_orde', 'serv_empr', 'serv_fili', 'serv_codi']
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

                    # Converter campos numéricos
                    try:
                        item['serv_orde'] = int(item['serv_orde'])
                        item['serv_empr'] = int(item['serv_empr'])
                        item['serv_fili'] = int(item['serv_fili'])
                        item['serv_quan'] = float(item.get('serv_quan', 0))
                        item['serv_unit'] = float(item.get('serv_unit', 0))
                        item['serv_tota'] = float(item.get('serv_tota', 0))
                    except (ValueError, TypeError) as e:
                        raise ValidationError({
                            'error': f"Erro ao converter valores numéricos: {str(e)}",
                            'item': item
                        })

                    # Gerar novo ID sequencial e número de sequência
                    item['serv_id'], item['serv_sequ'] = get_next_service_id(
                        banco, 
                        item['serv_orde'], 
                        item['serv_empr'], 
                        item['serv_fili']
                    )

                    serializer = self.get_serializer(data=item)
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save()
                    resposta['adicionados'].append(serializer.data)

                # Editar serviços existentes
                for item in editar:
                    if not all(k in item for k in ['serv_id', 'serv_orde', 'serv_empr', 'serv_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para edição",
                            'item': item
                        })

                    try:
                        obj = Ordemservicoservicos.objects.using(banco).get(
                            serv_id=item['serv_id'],
                            serv_orde=item['serv_orde'],
                            serv_empr=item['serv_empr'],
                            serv_fili=item['serv_fili']
                        )
                        serializer = self.get_serializer(obj, data=item, partial=True)
                        serializer.is_valid(raise_exception=True)
                        serializer.save()
                        resposta['editados'].append(serializer.data)
                    except Ordemservicoservicos.DoesNotExist:
                        logger.warning(f"Serviço não encontrado para edição: {item}")
                        continue

                # Remover serviços
                for item in remover:
                    if not all(k in item for k in ['serv_id', 'serv_orde', 'serv_empr', 'serv_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para remoção",
                            'item': item
                        })

                    Ordemservicoservicos.objects.using(banco).filter(
                        serv_id=item['serv_id'],
                        serv_orde=item['serv_orde'],
                        serv_empr=item['serv_empr'],
                        serv_fili=item['serv_fili']
                    ).delete()
                    resposta['removidos'].append(item['serv_id'])

            return Response(resposta)

        except ValidationError as e:
            logger.error(f"Erro de validação ao processar update_lista: {str(e)}")
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(f"Erro ao processar update_lista: {str(e)}")
            return Response({"error": str(e)}, status=400)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:  # Se criou com sucesso
            data = request.data
            self.atualizar_total_ordem(
                data.get('serv_empr'),
                data.get('serv_fili'),
                data.get('serv_orde')
            )
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:  # Se atualizou com sucesso
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.serv_empr,
                instance.serv_fili,
                instance.serv_orde
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.serv_empr, instance.serv_fili, instance.serv_orde
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:  # Se deletou com sucesso
            self.atualizar_total_ordem(empr, fili, orde)
        return response


class FotosViewSet(BaseMultiDBModelViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=["get"], url_path="imagens/(?P<etapa>antes|durante|depois)/(?P<image_id>\\d+)")
    def imagem_bin(self, request, etapa=None, image_id=None, slug=None):
        banco = self.get_banco()
        modelo = {
            "antes": Ordemservicoimgantes,
            "durante": Ordemservicoimgdurante,
            "depois": Ordemservicoimgdepois,
        }.get(etapa)
        campo = {
            "antes": "iman_imag",
            "durante": "imdu_imag",
            "depois": "imde_imag",
        }[etapa]
        obj = modelo.objects.using(banco).get(pk=image_id)
        img = getattr(obj, campo)
        return HttpResponse(img, content_type="image/jpeg")


class ImagemAntesViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = ImagemAntesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        banco = self.get_banco()
        iman_empr = self.request.query_params.get('iman_empr')
        iman_fili = self.request.query_params.get('iman_fili')
        iman_orde = self.request.query_params.get('iman_orde')
        
        queryset = Ordemservicoimgantes.objects.using(banco)
        
        if iman_empr:
            queryset = queryset.filter(iman_empr=iman_empr)
        if iman_fili:
            queryset = queryset.filter(iman_fili=iman_fili)
        if iman_orde:
            queryset = queryset.filter(iman_orde=iman_orde)
            
        return queryset.order_by('iman_id')
    
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()
        
        required_fields = ['iman_orde', 'iman_empr', 'iman_fili', 'imagem_upload']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {"error": f"Campo obrigatório '{field}' não fornecido"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        

        if not data.get('imagem_upload') or not data.get('imagem_upload').strip():
            return Response(
                {"error": "Imagem é obrigatória"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Gerar próximo ID se não fornecido
        if not data.get('iman_id'):
            data['iman_id'] = get_next_image_id(
                banco,
                data.get('iman_orde'),
                data.get('iman_empr'),
                data.get('iman_fili'),
                'antes'
            )
        
        # Gerar próximo código se não fornecido
        if not data.get('iman_codi'):
            data['iman_codi'] = get_next_image_id(
                banco,
                data.get('iman_orde'),
                data.get('iman_empr'),
                data.get('iman_fili'),
                'antes'
            )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ImagemDuranteViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = ImagemDuranteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        banco = self.get_banco()
        imdu_empr = self.request.query_params.get('imdu_empr')
        imdu_fili = self.request.query_params.get('imdu_fili')
        imdu_orde = self.request.query_params.get('imdu_orde')
        
        queryset = Ordemservicoimgdurante.objects.using(banco)
        
        if imdu_empr:
            queryset = queryset.filter(imdu_empr=imdu_empr)
        if imdu_fili:
            queryset = queryset.filter(imdu_fili=imdu_fili)
        if imdu_orde:
            queryset = queryset.filter(imdu_orde=imdu_orde)
            
        return queryset.order_by('imdu_id')
    
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()
        
        # Validar apenas campos obrigatórios essenciais
        required_fields = ['imdu_orde', 'imdu_empr', 'imdu_fili']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {"error": f"Campo obrigatório '{field}' não fornecido"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validar se imagem_upload não está vazia
        if not data.get('imagem_upload'):
            return Response(
                {"error": "Campo 'imagem_upload' é obrigatório e não pode estar vazio"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Gerar próximo ID se não fornecido
        if not data.get('imdu_id'):
            data['imdu_id'] = get_next_image_id(
                banco,
                data.get('imdu_orde'),
                data.get('imdu_empr'),
                data.get('imdu_fili'),
                'durante'
            )
        
        # Gerar próximo código se não fornecido
        if not data.get('imdu_codi'):
            data['imdu_codi'] = get_next_image_id(
                banco,
                data.get('imdu_orde'),
                data.get('imdu_empr'),
                data.get('imdu_fili'),
                'durante'
            )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ImagemDepoisViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = ImagemDepoisSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        banco = self.get_banco()
        imde_empr = self.request.query_params.get('imde_empr')
        imde_fili = self.request.query_params.get('imde_fili')
        imde_orde = self.request.query_params.get('imde_orde')
        
        queryset = Ordemservicoimgdepois.objects.using(banco)
        
        if imde_empr:
            queryset = queryset.filter(imde_empr=imde_empr)
        if imde_fili:
            queryset = queryset.filter(imde_fili=imde_fili)
        if imde_orde:
            queryset = queryset.filter(imde_orde=imde_orde)
            
        return queryset.order_by('imde_id')
    
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()
        
        # Validar apenas campos obrigatórios essenciais
        required_fields = ['imde_orde', 'imde_empr', 'imde_fili']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {"error": f"Campo obrigatório '{field}' não fornecido"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validar se imagem_upload não está vazia
        if not data.get('imagem_upload'):
            return Response(
                {"error": "Campo 'imagem_upload' é obrigatório e não pode estar vazio"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Gerar próximo ID se não fornecido
        if not data.get('imde_id'):
            data['imde_id'] = get_next_image_id(
                banco,
                data.get('imde_orde'),
                data.get('imde_empr'),
                data.get('imde_fili'),
                'depois'
            )
        
        # Gerar próximo código se não fornecido
        if not data.get('imde_codi'):
            data['imde_codi'] = get_next_image_id(
                banco,
                data.get('imde_orde'),
                data.get('imde_empr'),
                data.get('imde_fili'),
                'depois'
            )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)