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
from ..utils import get_next_item_number_sequence, get_next_service_id
from listacasamento.utils import get_next_item_number
from ..permissions import PodeVerOrdemDoSetor
from ..models import Os, PecasOs, ServicosOs
from .serializers import (
    OsSerializer, PecasOsSerializer, ServicosOsSerializer)
from django.db.models import Prefetch
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


class OsViewSet(BaseMultiDBModelViewSet):
    permission_classes = [IsAuthenticated, PodeVerOrdemDoSetor]
    modulo_necessario = 'O_S'
    serializer_class = OsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['os_stat_os', 'os_clie']
    ordering_fields = ['os_data_aber', 'os_data_fech']
    search_fields = ['os_prob_rela', 'os_obse']
   
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self):
        banco = self.get_banco()
        user_setor = self.request.user.setor

        qs = Os.objects.using(banco).all()

        return qs.order_by('-os_data_aber')
        
    @action(detail=True, methods=['post'])
    def finalizar_os(self, request, pk=None):
        """Endpoint para finalizar uma OS com validações"""
        os_instance = self.get_object()
        
        # Validações de negócio
        if os_instance.os_stat_os == 2:
            return Response(
                {'error': 'OS já finalizada'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar se tem peças ou serviços
        banco = self.get_banco()
        tem_pecas = PecasOs.objects.using(banco).filter(
            peca_os=os_instance.os_os
        ).exists()
        tem_servicos = ServicosOs.objects.using(banco).filter(
            serv_os=os_instance.os_os
        ).exists()
        
        if not tem_pecas and not tem_servicos:
            return Response(
                {'error': 'OS deve ter pelo menos uma peça ou serviço'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic(using=banco):
            os_instance.os_stat_os = 2
            os_instance.os_data_fech = timezone.now().date()
            os_instance.save(using=banco)
        
        return Response({'message': 'OS finalizada com sucesso'})

    def get_next_ordem_numero(self, empre, fili):
        banco = self.get_banco()
        ultimo = Os.objects.using(banco).filter(os_empr=empre, os_fili=fili).aggregate(Max('os_os'))['os_os__max']
        return (ultimo or 0) + 1

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()

        data['os_stat_os'] = 0
        if request.user and request.user.pk:
            data['os_usua_aber'] = request.user.pk

        empre = data.get('os_empr') or data.get('empr')
        fili = data.get('os_fili') or data.get('fili')
        if not empre or not fili:
            return Response({"detail": "Empresa e Filial são obrigatórios."}, status=400)

        data['os_os'] = self.get_next_ordem_numero(empre, fili)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            instance = serializer.save()
        logger.info(f"O.S. {instance.os_os} aberta por user {request.user.pk if request.user else 'anon'}")
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(
        detail=True, 
        methods=['post'],
        permission_classes=[IsAuthenticated]
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


class PecasOsViewSet(BaseMultiDBModelViewSet,ModelViewSet):
    serializer_class = PecasOsSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
 
   
    def atualizar_total_ordem(self, peca_empr, peca_fili, peca_os):
        banco = self.get_banco()
        try:
            ordem = Os.objects.using(banco).get(
                os_empr=peca_empr,
                os_fili=peca_fili,
                os_os=peca_os
            )
            ordem.calcular_total()
            ordem.save(using=banco)
        except Os.DoesNotExist:
            logger.error(f"Ordem de serviço não encontrada: {peca_os}")

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        peca_empr = self.request.query_params.get('peca_empr')
        peca_fili = self.request.query_params.get('peca_fili')
        peca_os = self.request.query_params.get('peca_os')

        if not all([peca_empr, peca_fili, peca_os]):
            logger.warning("Parâmetros obrigatórios não fornecidos (peca_empr, peca_fili, peca_os)")
            return PecasOs.objects.none()

        queryset = PecasOs.objects.using(banco).filter(
            peca_empr=peca_empr,
            peca_fili=peca_fili,
            peca_os=peca_os
        )

        logger.info(f"Parâmetros recebidos: peca_empr={peca_empr}, peca_fili={peca_fili}, peca_os={peca_os}")
        logger.info(f"Queryset filtrado: {queryset.query}")
        return queryset.order_by('peca_item')

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        peca_item = self.kwargs.get('pk')
        peca_os = self.request.query_params.get("peca_os")
        peca_empr = self.request.query_params.get("peca_empr")
        peca_fili = self.request.query_params.get("peca_fili")

        if not all([peca_os, peca_empr, peca_fili, peca_item]):
            raise ValidationError("Parâmetros peca_os, peca_empr, peca_fili e pk (peca_item) são obrigatórios.")

        try:
            return self.get_queryset().get(
                peca_item=peca_item,
                peca_os=peca_os,
                peca_empr=peca_empr,
                peca_fili=peca_fili
            )
        except PecasOs.DoesNotExist:
            raise NotFound("peca não encontrado na lista especificada.")
        except PecasOs.MultipleObjectsReturned:
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
                    campos_obrigatorios = ['peca_os', 'peca_empr', 'peca_fili', 'peca_prod']
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

                    # Converter campos numéricos
                    try:
                        item['peca_os'] = int(item['peca_os'])
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

                    item['peca_item'] = get_next_item_number_sequence(
                        banco, item['peca_os'], item['peca_empr'], item['peca_fili']
                    )
                    serializer = PecasOsSerializer(data=item, context={'banco': banco})
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save()

                    obj_refetch = PecasOs.objects.using(banco).get(
                        peca_empr=obj.peca_empr,
                        peca_fili=obj.peca_fili,
                        peca_os=obj.peca_os,
                        peca_item=obj.peca_item,
                    )
                    resposta['adicionados'].append(
                        PecasOsSerializer(obj_refetch, context={'banco': banco}).data
                    )

                # Validar e editar itens existentes
                for item in editar:
                    if not all(k in item for k in ['peca_item', 'peca_os', 'peca_empr', 'peca_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para edição",
                            'item': item
                        })

                    try:
                        obj = PecasOs.objects.using(banco).get(
                            peca_item=item['peca_item'],
                            peca_os=item['peca_os'],
                            peca_empr=item['peca_empr'],
                            peca_fili=item['peca_fili']
                        )
                    except PecasOs.DoesNotExist:
                        logger.warning(f"Peça não encontrada para edição: {item}")
                        continue

                    serializer = PecasOsSerializer(obj, data=item, context={'banco': banco}, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    resposta['editados'].append(serializer.data)

                # Validar e remover itens
                for item in remover:
                    if not all(k in item for k in ['peca_item', 'peca_os', 'peca_empr', 'peca_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para remoção",
                            'item': item
                        })

                    PecasOs.objects.using(banco).filter(
                        peca_item=item['peca_item'],
                        peca_os=item['peca_os'],
                        peca_empr=item['peca_empr'],
                        peca_fili=item['peca_fili']
                    ).delete()
                    resposta['removidos'].append(item['peca_item'])

            return Response(resposta)
            print(resposta)

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
                data.get('peca_os')
            )
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:  # Se atualizou com sucesso
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.peca_empr,
                instance.peca_fili,
                instance.peca_os
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.peca_empr, instance.peca_fili, instance.peca_os
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:  # Se deletou com sucesso
            self.atualizar_total_ordem(empr, fili, orde)
        return response

class ServicosOsViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'O_S'
    serializer_class = ServicosOsSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def atualizar_total_ordem(self, serv_empr, serv_fili, serv_os):
        banco = self.get_banco()
        try:
            ordem = Os.objects.using(banco).get(
                os_empr=serv_empr,
                os_fili=serv_fili,
                os_os=serv_os
            )
            ordem.calcular_total()
            ordem.save(using=banco)
        except Os.DoesNotExist:
            logger.error(f"Ordem de serviço não encontrada: {serv_os}")

    def get_queryset(self):
        banco = self.get_banco()
        serv_empr = self.request.query_params.get('serv_empr') or self.request.query_params.get('empr')
        serv_fili = self.request.query_params.get('serv_fili') or self.request.query_params.get('fili')
        serv_os = self.request.query_params.get('serv_os') or self.request.query_params.get('ordem')

        if not all([serv_empr, serv_fili, serv_os]):
            logger.warning("Parâmetros obrigatórios não fornecidos (serv_empr/empr, serv_fili/fili, serv_os/ordem)")
            return ServicosOs.objects.using(banco).none()

        qs = ServicosOs.objects.using(banco).filter(
            serv_empr=serv_empr,
            serv_fili=serv_fili,
            serv_os=serv_os
        )
        
        logger.info(f"Filtrando serviços com: ordem={serv_os}, empresa={serv_empr}, filial={serv_fili}")
        return qs.order_by('serv_item')

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
                # ADICIONAR
                for item in adicionar:
                    # Verifica campos obrigatórios
                    campos_obrigatorios = ['serv_os', 'serv_empr', 'serv_fili', 'serv_prod']
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

                    # Converte campos numéricos
                    try:
                        item['serv_os'] = int(item['serv_os'])
                        item['serv_empr'] = int(item['serv_empr'])
                        item['serv_fili'] = int(item['serv_fili'])
                        item['serv_quan'] = float(item.get('serv_quan') or 0)
                        item['serv_unit'] = float(item.get('serv_unit') or 0)
                        item['serv_tota'] = float(item.get('serv_tota') or (item['serv_quan'] * item['serv_unit']))
                    except (ValueError, TypeError) as e:
                        raise ValidationError({
                            'error': f"Erro ao converter valores numéricos: {str(e)}",
                            'item': item
                        })

                    # Gera novo ID sequencial (recebe tupla)
                    novo_id, _ = get_next_service_id(
                        banco,
                        item['serv_os'],
                        item['serv_empr'],
                        item['serv_fili']
                    )
                    item['serv_item'] = novo_id

                    # Cria via serializer
                    serializer = self.get_serializer(data=item, context={'banco': banco})
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save()
                    resposta['adicionados'].append(serializer.data)

                # EDITAR
                for item in editar:
                    if not all(k in item for k in ['serv_item', 'serv_os', 'serv_empr', 'serv_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para edição",
                            'item': item
                        })

                    # Normaliza numéricos e calcula total quando necessário
                    try:
                        serv_quan = float(item.get('serv_quan') or 0)
                        serv_unit = float(item.get('serv_unit') or 0)
                        serv_desc = float(item.get('serv_desc') or 0)
                        serv_tota = float(item.get('serv_tota') or (serv_quan * serv_unit))
                    except (ValueError, TypeError) as e:
                        raise ValidationError({
                            'error': f"Erro ao converter valores numéricos na edição: {str(e)}",
                            'item': item
                        })

                    defaults = {
                        'serv_prod': item.get('serv_prod'),
                        'serv_quan': serv_quan,
                        'serv_unit': serv_unit,
                        'serv_tota': serv_tota,
                        'serv_desc': serv_desc,
                        'serv_obse': item.get('serv_obse'),
                        'serv_prof': item.get('serv_prof'),
                        'serv_data': item.get('serv_data'),
                        'serv_impr': item.get('serv_impr'),
                        'serv_stat': item.get('serv_stat'),
                        'serv_data_hora_impr': item.get('serv_data_hora_impr'),
                        'serv_stat_seto': item.get('serv_stat_seto'),
                    }

                    updated = ServicosOs.objects.using(banco).filter(
                        serv_item=item['serv_item'],
                        serv_os=item['serv_os'],
                        serv_empr=item['serv_empr'],
                        serv_fili=item['serv_fili']
                    ).update(**defaults)

                    if updated:
                        obj = ServicosOs.objects.using(banco).get(
                            serv_item=item['serv_item'],
                            serv_os=item['serv_os'],
                            serv_empr=item['serv_empr'],
                            serv_fili=item['serv_fili']
                        )
                        resposta['editados'].append(ServicosOsSerializer(obj, context={'banco': banco}).data)
                    else:
                        logger.warning(f"Serviço não encontrado para edição: {item}")

                # REMOVER
                for item in remover:
                    if not all(k in item for k in ['serv_item', 'serv_os', 'serv_empr', 'serv_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para remoção",
                            'item': item
                        })

                    deleted, _ = ServicosOs.objects.using(banco).filter(
                        serv_item=item['serv_item'],
                        serv_os=item['serv_os'],
                        serv_empr=item['serv_empr'],
                        serv_fili=item['serv_fili']
                    ).delete()

                    if deleted:
                        resposta['removidos'].append(item['serv_item'])

                # Sequência é garantida pelo gerador (formato ordem+NNN); não compactar

            return Response(resposta)

        except ValidationError as e:
            logger.error(f"Erro de validação ao processar update_lista: {str(e)}")
            return Response(e.detail, status=400)

        except Exception as e:
            logger.exception("Erro inesperado ao processar update_lista")
            return Response({"error": str(e)}, status=400)


    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:  # Se criou com sucesso
            data = request.data
            self.atualizar_total_ordem(
                data.get('serv_empr'),
                data.get('serv_fili'),
                data.get('serv_os')
            )
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:  # Se atualizou com sucesso
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.serv_empr,
                instance.serv_fili,
                instance.serv_os
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.serv_empr, instance.serv_fili, instance.serv_os
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:  # Se deletou com sucesso
            self.atualizar_total_ordem(empr, fili, orde)
        return response

