from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from django.db import transaction, IntegrityError

from .base import BaseMultiDBModelViewSet
from ..models import Ordemservico, Ordemservicopecas, Ordemservicoservicos
from ..serializers import OrdemServicoPecasSerializer, OrdemServicoServicosSerializer
from ..utils import get_next_item_number_sequence, get_next_service_id
from ..handlers.dominio_handler import tratar_erro
from core.registry import get_licenca_db_config

import logging
logger = logging.getLogger(__name__)

class OrdemServicoPecasViewSet(BaseMultiDBModelViewSet, ModelViewSet):
    serializer_class = OrdemServicoPecasSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
   
    def atualizar_total_ordem(self, peca_empr, peca_fili, peca_orde):
        banco = self.get_banco()
        try:
            # Deferir campos de data que podem conter valores inválidos (ano < 1900 ou > 9999)
            # Isso evita erros como "ValueError: year -18 is out of range" ao carregar o objeto
            ordem = Ordemservico.objects.using(banco).defer(
                'orde_data_repr', 
                'orde_data_fech', 
                'orde_nf_data', 
                'orde_ulti_alte'
            ).get(
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

        peca_empr = self.request.query_params.get('peca_empr') or self.request.query_params.get('empr')
        peca_fili = self.request.query_params.get('peca_fili') or self.request.query_params.get('fili')
        peca_orde = self.request.query_params.get('peca_orde') or self.request.query_params.get('ordem')

        if not all([peca_empr, peca_fili, peca_orde]):
            logger.warning("Parâmetros obrigatórios não fornecidos (peca_empr, peca_fili, peca_orde)")
            return Ordemservicopecas.objects.none()

        queryset = Ordemservicopecas.objects.using(banco).filter(
            peca_empr=peca_empr,
            peca_fili=peca_fili,
            peca_orde=peca_orde
        )

        logger.info(f"Parâmetros recebidos: peca_empr={peca_empr}, peca_fili={peca_fili}, peca_orde={peca_orde}")
        return queryset.order_by('peca_id')

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        peca_id = self.kwargs.get('pk')
        peca_empr = self.request.query_params.get('peca_empr') or self.request.query_params.get('empr')
        peca_fili = self.request.query_params.get('peca_fili') or self.request.query_params.get('fili')
        peca_orde = self.request.query_params.get('peca_orde') or self.request.query_params.get('ordem')

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
        # Nota: peca_pedi parece ser um campo para verificar se já foi pedido, mas não vi no model. 
        # Mantendo lógica original.
        try:
            peca = self.get_object()
            if hasattr(peca, 'peca_pedi') and peca.peca_pedi != 0:
                return Response({"detail": "Não é possível excluir peca já associado a pedido."}, status=400)
            
            empr, fili, orde = peca.peca_empr, peca.peca_fili, peca.peca_orde
            response = super().destroy(request, *args, **kwargs)
            if response.status_code == 204:
                self.atualizar_total_ordem(empr, fili, orde)
            return response
        except Exception as e:
            return tratar_erro(e)

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

            response = super().create(request, *args, **kwargs)
            if response.status_code == 201:
                data = request.data
                self.atualizar_total_ordem(
                    data.get('peca_empr'),
                    data.get('peca_fili'),
                    data.get('peca_orde')
                )
            return response

        except Exception as e:
            return tratar_erro(e)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.peca_empr,
                instance.peca_fili,
                instance.peca_orde
            )
        return response

    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=404)

        data = request.data
        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])
        
        default_empr = data.get('peca_empr') or data.get('empr') or data.get("X-Empresa")
        default_fili = data.get('peca_fili') or data.get('fili') or data.get("X-Filial")
        default_orde = data.get('peca_orde') or data.get('ordem')

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}
        affected_orders = set()

        try:
            with transaction.atomic(using=banco):
                # Validar e adicionar novos itens
                for item in adicionar:
                    if default_empr is not None:
                         item['peca_empr'] = default_empr
                    if default_fili is not None:
                        item['peca_fili'] = default_fili
                    if default_orde is not None:
                        item['peca_orde'] = default_orde
                    
                    campos_obrigatorios = ['peca_orde', 'peca_empr', 'peca_fili', 'peca_codi']
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

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

                    # Validar existência da ordem sem carregar o objeto inteiro
                    # para evitar erro de datas inválidas
                    if not Ordemservico.objects.using(banco).filter(
                        orde_empr=item['peca_empr'],
                        orde_fili=item['peca_fili'],
                        orde_nume=item['peca_orde']
                    ).exists():
                        raise ValidationError({
                            'error': (
                                f"Ordem de serviço não encontrada para empresa={item['peca_empr']}, "
                                f"filial={item['peca_fili']}, ordem={item['peca_orde']}"
                            ),
                            'item': item
                        })

                    # try:
                    #     Ordemservico.objects.using(banco).get(
                    #         orde_empr=item['peca_empr'],
                    #         orde_fili=item['peca_fili'],
                    #         orde_nume=item['peca_orde']
                    #     )
                    # except Ordemservico.DoesNotExist:
                    #     raise ValidationError({
                    #         'error': (
                    #             f"Ordem de serviço não encontrada para empresa={item['peca_empr']}, "
                    #             f"filial={item['peca_fili']}, ordem={item['peca_orde']}"
                    #         ),
                    #         'item': item
                    #     })

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
                    affected_orders.add((obj.peca_empr, obj.peca_fili, obj.peca_orde))

                # Validar e editar itens existentes
                for item in editar:
                    if default_empr is not None:
                        item['peca_empr'] = default_empr
                    if default_fili is not None:
                        item['peca_fili'] = default_fili
                    if default_orde is not None:
                        item['peca_orde'] = default_orde

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
                    obj = serializer.save()
                    resposta['editados'].append(serializer.data)
                    affected_orders.add((obj.peca_empr, obj.peca_fili, obj.peca_orde))

                # Validar e remover itens
                for item in remover:
                    if default_empr is not None:
                        item['peca_empr'] = default_empr
                    if default_fili is not None:
                        item['peca_fili'] = default_fili
                    if default_orde is not None:
                        item['peca_orde'] = default_orde

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
                    affected_orders.add((item['peca_empr'], item['peca_fili'], item['peca_orde']))

            # Atualizar totais das ordens afetadas
            for (empr, fili, orde) in affected_orders:
                try:
                    self.atualizar_total_ordem(empr, fili, orde)
                except Exception as e:
                    logger.error(f"Falha ao atualizar total da OS (empr={empr}, fili={fili}, orde={orde}): {e}")

            return Response(resposta)

        except Exception as e:
            logger.error(f"Erro ao processar update_lista: {str(e)} | payload={data}")
            return tratar_erro(e)


class OrdemServicoServicosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'OrdemdeServico'
    serializer_class = OrdemServicoServicosSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def atualizar_total_ordem(self, serv_empr, serv_fili, serv_orde):
        banco = self.get_banco()
        try:
            # Deferir campos de data que podem conter valores inválidos (ano < 1900 ou > 9999)
            # Isso evita erros como "ValueError: year -18 is out of range" ao carregar o objeto
            ordem = Ordemservico.objects.using(banco).defer(
                'orde_data_repr', 
                'orde_data_fech', 
                'orde_nf_data', 
                'orde_ulti_alte'
            ).get(
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

        default_empr = (
            data.get('serv_empr') or data.get('empr') or request.headers.get('X-Empresa')
        )
        default_fili = (
            data.get('serv_fili') or data.get('fili') or request.headers.get('X-Filial')
        )
        default_orde = (
            data.get('serv_orde') or data.get('ordem')
        )

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}
        affected_orders = set()

        try:
            with transaction.atomic(using=banco):
                # Validar e adicionar novos itens
                for item in adicionar:
                    if default_empr is not None:
                        item['serv_empr'] = default_empr
                    if default_fili is not None:
                        item['serv_fili'] = default_fili
                    if default_orde is not None:
                        item['serv_orde'] = default_orde
                    
                    campos_obrigatorios = ['serv_orde', 'serv_empr', 'serv_fili', 'serv_codi']
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

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

                    if not Ordemservico.objects.using(banco).filter(
                        orde_empr=item['serv_empr'],
                        orde_fili=item['serv_fili'],
                        orde_nume=item['serv_orde']
                    ).exists():
                        raise ValidationError({
                            'error': (
                                f"Ordem de serviço não encontrada para empresa={item['serv_empr']}, "
                                f"filial={item['serv_fili']}, ordem={item['serv_orde']}"
                            ),
                            'item': item
                        })

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
                    affected_orders.add((obj.serv_empr, obj.serv_fili, obj.serv_orde))

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
                        obj = serializer.save()
                        resposta['editados'].append(serializer.data)
                        affected_orders.add((obj.serv_empr, obj.serv_fili, obj.serv_orde))
                    except Ordemservicoservicos.DoesNotExist:
                        logger.warning(f"Serviço não encontrado para edição: {item}")
                        continue

                # Remover serviços
                for item in remover:
                    if default_empr is not None:
                        item['serv_empr'] = default_empr
                    if default_fili is not None:
                        item['serv_fili'] = default_fili
                    if default_orde is not None:
                        item['serv_orde'] = default_orde
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
                    affected_orders.add((item['serv_empr'], item['serv_fili'], item['serv_orde']))

            # Atualizar totais das ordens afetadas
            for (empr, fili, orde) in affected_orders:
                try:
                    self.atualizar_total_ordem(empr, fili, orde)
                except Exception as e:
                    logger.error(f"Falha ao atualizar total da OS (empr={empr}, fili={fili}, orde={orde}): {e}")

            return Response(resposta)

        except Exception as e:
            logger.error(f"Erro ao processar update_lista: {str(e)}")
            return tratar_erro(e)

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            if response.status_code == 201:
                data = request.data
                self.atualizar_total_ordem(
                    data.get('serv_empr'),
                    data.get('serv_fili'),
                    data.get('serv_orde')
                )
            return response
        except Exception as e:
            return tratar_erro(e)

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            if response.status_code == 200:
                instance = self.get_object()
                self.atualizar_total_ordem(
                    instance.serv_empr,
                    instance.serv_fili,
                    instance.serv_orde
                )
            return response
        except Exception as e:
            return tratar_erro(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            empr, fili, orde = instance.serv_empr, instance.serv_fili, instance.serv_orde
            response = super().destroy(request, *args, **kwargs)
            if response.status_code == 204:
                self.atualizar_total_ordem(empr, fili, orde)
            return response
        except Exception as e:
            return tratar_erro(e)
