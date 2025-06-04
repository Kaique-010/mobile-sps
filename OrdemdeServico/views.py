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
from OrdemdeServico.utils import get_next_item_number_sequence, get_next_service_id, get_next_image_id
from listacasamento.utils import get_next_item_number
from .permissions import PodeVerOrdemDoSetor
from .models import (
    Ordemservico, Ordemservicopecas, Ordemservicoservicos,
    Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois
)
from .serializers import (
    OrdemServicoSerializer, OrdemServicoPecasSerializer, OrdemServicoServicosSerializer,
    ImagemAntesSerializer, ImagemDuranteSerializer, ImagemDepoisSerializer
)
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.decorator import modulo_necessario, ModuloRequeridoMixin

import logging
logger = logging.getLogger(__name__)


class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]

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
        banco = self.get_banco()
        data = request.data
        is_many = isinstance(data, list)
        serializer = self.get_serializer(data=data, many=is_many)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        banco = self.get_banco()
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data)


class OrdemServicoViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = OrdemServicoSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['orde_stat_orde', 'orde_prio', 'orde_tipo', 'orde_enti']
    ordering_fields = ['orde_data_aber', 'orde_data_fech', 'orde_prio']
    search_fields = ['orde_prob', 'orde_defe_desc', 'orde_obse']
    permission_classes = [IsAuthenticated, PodeVerOrdemDoSetor]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self):
        banco = self.get_banco()
        user_setor = self.request.user.setor
        qs = Ordemservico.objects.using(banco)
        if user_setor.osfs_codi != 6:
            qs = qs.filter(orde_seto=user_setor.osfs_codi)
        return qs.order_by('orde_data_aber')

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
        permission_classes=[IsAuthenticated]  # Removendo a restrição de setor para esta ação específica
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
    modulo_necessario = 'ordemservico'
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


class BaseImagemViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get_queryset(self):
        banco = self.get_banco()
        ordem_id = self.request.query_params.get('ordem')
        qs = self.queryset.using(banco)
        return qs.filter(**{self.ordem_field: ordem_id}) if ordem_id else qs

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
                # Validar e adicionar novas imagens
                for item in adicionar:
                    # Validar campos obrigatórios
                    campos_obrigatorios = [
                        self.ordem_field, 
                        self.empresa_field, 
                        self.filial_field, 
                        self.codigo_field,
                        self.imagem_field
                    ]
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

                    # Converter campos numéricos
                    try:
                        item[self.ordem_field] = int(item[self.ordem_field])
                        item[self.empresa_field] = int(item[self.empresa_field])
                        item[self.filial_field] = int(item[self.filial_field])
                        item[self.codigo_field] = int(item[self.codigo_field])
                        
                        # Converter coordenadas se presentes
                        if 'img_latitude' in item:
                            item['img_latitude'] = float(item['img_latitude'])
                        if 'img_longitude' in item:
                            item['img_longitude'] = float(item['img_longitude'])
                    except (ValueError, TypeError) as e:
                        raise ValidationError({
                            'error': f"Erro ao converter valores numéricos: {str(e)}",
                            'item': item
                        })

                    # Gerar novo ID sequencial
                    item[self.id_field] = get_next_image_id(
                        banco,
                        item[self.ordem_field],
                        item[self.empresa_field],
                        item[self.filial_field],
                        self.tipo_imagem
                    )

                    serializer = self.get_serializer(data=item)
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save()
                    resposta['adicionados'].append(serializer.data)

                # Editar imagens existentes
                for item in editar:
                    campos_chave = [self.id_field, self.ordem_field, self.empresa_field, self.filial_field]
                    if not all(k in item for k in campos_chave):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para edição",
                            'item': item
                        })

                    try:
                        filtro = {campo: item[campo] for campo in campos_chave}
                        obj = self.queryset.using(banco).get(**filtro)
                        serializer = self.get_serializer(obj, data=item, partial=True)
                        serializer.is_valid(raise_exception=True)
                        serializer.save()
                        resposta['editados'].append(serializer.data)
                    except self.queryset.model.DoesNotExist:
                        logger.warning(f"Imagem não encontrada para edição: {item}")
                        continue

                # Remover imagens
                for item in remover:
                    campos_chave = [self.id_field, self.ordem_field, self.empresa_field, self.filial_field]
                    if not all(k in item for k in campos_chave):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para remoção",
                            'item': item
                        })

                    filtro = {campo: item[campo] for campo in campos_chave}
                    self.queryset.using(banco).filter(**filtro).delete()
                    resposta['removidos'].append(item[self.id_field])

            return Response(resposta)

        except ValidationError as e:
            logger.error(f"Erro de validação ao processar update_lista: {str(e)}")
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(f"Erro ao processar update_lista: {str(e)}")
            return Response({"error": str(e)}, status=400)


class ImagemAntesViewSet(BaseImagemViewSet):
    serializer_class = ImagemAntesSerializer
    queryset = Ordemservicoimgantes.objects.all()
    tipo_imagem = 'antes'
    
    # Campos específicos para mapeamento
    id_field = 'iman_id'
    ordem_field = 'iman_orde'
    empresa_field = 'iman_empr'
    filial_field = 'iman_fili'
    codigo_field = 'iman_codi'
    imagem_field = 'iman_imag'


class ImagemDuranteViewSet(BaseImagemViewSet):
    serializer_class = ImagemDuranteSerializer
    queryset = Ordemservicoimgdurante.objects.all()
    tipo_imagem = 'durante'
    
    # Campos específicos para mapeamento
    id_field = 'imdu_id'
    ordem_field = 'imdu_orde'
    empresa_field = 'imdu_empr'
    filial_field = 'imdu_fili'
    codigo_field = 'imdu_codi'
    imagem_field = 'imdu_imag'


class ImagemDepoisViewSet(BaseImagemViewSet):
    serializer_class = ImagemDepoisSerializer
    queryset = Ordemservicoimgdepois.objects.all()
    tipo_imagem = 'depois'
    
    # Campos específicos para mapeamento
    id_field = 'imde_id'
    ordem_field = 'imde_orde'
    empresa_field = 'imde_empr'
    filial_field = 'imde_fili'
    codigo_field = 'imde_codi'
    imagem_field = 'imde_imag'


class FotosViewSet(BaseMultiDBModelViewSet):
    """
    ViewSet compatível com o endpoint legado /fotos/
    Combina as imagens de antes, durante e depois em uma única resposta
    """
    modulo_necessario = 'ordemservico'
    permission_classes = [IsAuthenticated]
    serializer_class = ImagemAntesSerializer  # Default serializer, será alterado conforme necessário

    def get_queryset(self):
        banco = self.get_banco()
        ordem_id = self.request.query_params.get('foto_orde')
        empresa_id = self.request.query_params.get('foto_empr')
        filial_id = self.request.query_params.get('foto_fili')
        
        if not all([ordem_id, empresa_id, filial_id]):
            return []

        # Combina as imagens de todos os tipos
        antes = Ordemservicoimgantes.objects.using(banco).filter(
            iman_orde=ordem_id,
            iman_empr=empresa_id,
            iman_fili=filial_id
        )
        durante = Ordemservicoimgdurante.objects.using(banco).filter(
            imdu_orde=ordem_id,
            imdu_empr=empresa_id,
            imdu_fili=filial_id
        )
        depois = Ordemservicoimgdepois.objects.using(banco).filter(
            imde_orde=ordem_id,
            imde_empr=empresa_id,
            imde_fili=filial_id
        )

        return {
            'antes': antes,
            'durante': durante,
            'depois': depois
        }

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset:
            return Response([])

        response_data = {
            'antes': ImagemAntesSerializer(
                queryset['antes'], 
                many=True, 
                context=self.get_serializer_context()
            ).data,
            'durante': ImagemDuranteSerializer(
                queryset['durante'], 
                many=True, 
                context=self.get_serializer_context()
            ).data,
            'depois': ImagemDepoisSerializer(
                queryset['depois'], 
                many=True, 
                context=self.get_serializer_context()
            ).data
        }

        return Response(response_data)

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request, *args, **kwargs):
        """
        Endpoint para upload de imagens.
        Espera os seguintes parâmetros em FormData:
        - foto: objeto com {uri, name, type}
        - foto_momento: 'antes', 'durante' ou 'depois'
        - foto_orde: número da ordem
        - foto_empr: empresa
        - foto_fili: filial
        - foto_desc: descrição da foto (opcional)
        """
        try:
            # Log dos headers para debug
            logger.info(f"Headers recebidos: {request.headers}")
            
            banco = self.get_banco()
            
            # Extrair dados do FormData
            data = {}
            if hasattr(request.data, '_parts'):
                for part in request.data._parts:
                    if len(part) == 2:
                        key, value = part
                        if isinstance(value, dict) and key == 'foto':
                            data[key] = value
                        else:
                            data[key] = value
            else:
                data = request.data

            logger.info(f"Dados recebidos no upload: {data}")
            
            # Validar parâmetros obrigatórios
            required_fields = ['foto', 'foto_momento', 'foto_orde', 'foto_empr', 'foto_fili']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                error_msg = f'Campos obrigatórios ausentes: {", ".join(missing_fields)}'
                logger.error(error_msg)
                return Response({'error': error_msg}, status=400)

            # Mapear momento para o tipo correto
            momento_mapping = {
                'antes': 'antes',
                'durante': 'durante',
                'depois': 'depois'
            }
            
            momento = data.get('foto_momento', '').lower()
            if momento not in momento_mapping:
                error_msg = 'Momento inválido. Use: antes, durante ou depois'
                logger.error(error_msg)
                return Response({'error': error_msg}, status=400)
                
            tipo = momento_mapping[momento]
            
            # Mapear tipo para o modelo e serializer corretos
            type_mapping = {
                'antes': (Ordemservicoimgantes, ImagemAntesSerializer, 'iman'),
                'durante': (Ordemservicoimgdurante, ImagemDuranteSerializer, 'imdu'),
                'depois': (Ordemservicoimgdepois, ImagemDepoisSerializer, 'imde')
            }
            
            Model, Serializer, prefix = type_mapping[tipo]

            # Processar a foto
            foto_data = data.get('foto', {})
            if not foto_data or not foto_data.get('uri'):
                error_msg = 'Dados da foto inválidos'
                logger.error(error_msg)
                return Response({'error': error_msg}, status=400)

            # Ler o arquivo da URI
            import urllib.request
            from urllib.parse import unquote
            import base64

            # Remover o prefixo 'file://' e decodificar a URL
            file_path = unquote(foto_data['uri'].replace('file://', ''))
            
            try:
                with open(file_path, 'rb') as image_file:
                    image_data = image_file.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
            except Exception as e:
                error_msg = f'Erro ao ler arquivo de imagem: {str(e)}'
                logger.error(error_msg)
                return Response({'error': error_msg}, status=400)
            
            # Preparar dados para o serializer
            serializer_data = {
                f'{prefix}_empr': int(data['foto_empr']),
                f'{prefix}_fili': int(data['foto_fili']),
                f'{prefix}_orde': int(data['foto_orde']),
                f'{prefix}_codi': get_next_image_id(
                    banco,
                    int(data['foto_orde']),
                    int(data['foto_empr']),
                    int(data['foto_fili']),
                    tipo
                ),
                'imagem_upload': image_base64,
                f'{prefix}_come': data.get('foto_desc', '')
            }
            
            logger.info(f"Tentando salvar imagem com dados: {serializer_data}")
            
            serializer = Serializer(data=serializer_data, context={'banco': banco})
            if not serializer.is_valid():
                error_msg = f'Erro de validação: {serializer.errors}'
                logger.error(error_msg)
                return Response({'error': error_msg}, status=400)

            with transaction.atomic(using=banco):
                instance = serializer.save()
            
            logger.info(f"Imagem salva com sucesso: {instance.pk}")
            return Response(serializer.data, status=201)
                
        except ValueError as e:
            error_msg = f'Erro de conversão de dados: {str(e)}'
            logger.error(error_msg)
            return Response({'error': error_msg}, status=400)
        except Exception as e:
            error_msg = f'Erro ao salvar imagem: {str(e)}'
            logger.error(error_msg)
            return Response({'error': error_msg}, status=400)