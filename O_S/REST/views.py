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
from ..models import Os, PecasOs, ServicosOs, OsHora
from .serializers import (
                            OsSerializer, PecasOsSerializer, 
                            ServicosOsSerializer, OsHoraSerializer)
from django.db import models
from django.db.models import Prefetch
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.decorator import modulo_necessario, ModuloRequeridoMixin

import logging
logger = logging.getLogger(__name__)


class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):

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
    permission_classes = [PodeVerOrdemDoSetor]
    serializer_class = OsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['os_stat_os', 'os_clie']
    ordering_fields = ['os_data_aber', 'os_data_fech']
    search_fields = ['os_prob_rela', 'os_obse']
   
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    def get_queryset(self):
        banco = self.get_banco()
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


class PecasOsViewSet(BaseMultiDBModelViewSet):
    serializer_class = PecasOsSerializer
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
            logger.error(f"Ordem não encontrada para recalcular: {peca_os}")

    def get_queryset(self):
        banco = self.get_banco()

        peca_empr = self.request.query_params.get('peca_empr')
        peca_fili = self.request.query_params.get('peca_fili')
        peca_os = self.request.query_params.get('peca_os')

        if not all([peca_empr, peca_fili, peca_os]):
            logger.warning("Query sem parâmetros (peca_empr, peca_fili, peca_os). Retornando vazio.")
            return PecasOs.objects.none()

        qs = PecasOs.objects.using(banco).filter(
            peca_empr=peca_empr,
            peca_fili=peca_fili,
            peca_os=peca_os
        )

        return qs.order_by('peca_item')

    def get_object(self):
        banco = self.get_banco()

        peca_item = self.kwargs.get('pk')
        peca_os = self.request.query_params.get("peca_os")
        peca_empr = self.request.query_params.get("peca_empr")
        peca_fili = self.request.query_params.get("peca_fili")

        if not all([peca_os, peca_empr, peca_fili, peca_item]):
            raise ValidationError("Faltam parâmetros: peca_item, peca_os, peca_empr, peca_fili.")

        try:
            return PecasOs.objects.using(banco).get(
                peca_item=peca_item,
                peca_os=peca_os,
                peca_empr=peca_empr,
                peca_fili=peca_fili
            )
        except PecasOs.DoesNotExist:
            raise NotFound("Peça não encontrada.")
        except PecasOs.MultipleObjectsReturned:
            raise ValidationError("Chave composta retornou múltiplos registros.")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['banco'] = self.get_banco()
        return ctx



    # CREATE único e correto
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()

        try:
            is_many = isinstance(request.data, list)
            serializer = self.get_serializer(data=request.data, many=is_many)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic(using=banco):
                objs = serializer.save()

            # recalcula total da OS
            if is_many:
                exemplo = request.data[0]
            else:
                exemplo = request.data

            self.atualizar_total_ordem(
                exemplo.get('peca_empr'),
                exemplo.get('peca_fili'),
                exemplo.get('peca_os')
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except IntegrityError:
            return Response({'detail': 'Erro de integridade.'}, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({'detail': str(e)}, status=500)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.peca_empr, instance.peca_fili, instance.peca_os
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.peca_empr, instance.peca_fili, instance.peca_os
        response = super().destroy(request, *args, **kwargs)

        if response.status_code == 204:
            self.atualizar_total_ordem(empr, fili, orde)

        return response

    # atualização em lote padronizada
    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = self.get_banco()
        data = request.data

        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):

                # ADICIONAR
                for item in adicionar:
                    campos_obrig = ['peca_os', 'peca_empr', 'peca_fili', 'peca_prod']
                    faltando = [c for c in campos_obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Faltam campos: {', '.join(faltando)}")

                    item['peca_item'] = get_next_item_number_sequence(
                        banco, item['peca_os'], item['peca_empr'], item['peca_fili']
                    )

                    s = PecasOsSerializer(data=item, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    obj = s.save()

                    resposta['adicionados'].append(
                        PecasOsSerializer(obj, context={'banco': banco}).data
                    )

                # EDITAR
                for item in editar:
                    required = ['peca_item', 'peca_os', 'peca_empr', 'peca_fili']
                    if not all(k in item for k in required):
                        raise ValidationError("Campos obrigatórios para edição faltando.")

                    try:
                        obj = PecasOs.objects.using(banco).get(
                            peca_item=item['peca_item'],
                            peca_os=item['peca_os'],
                            peca_empr=item['peca_empr'],
                            peca_fili=item['peca_fili']
                        )
                    except PecasOs.DoesNotExist:
                        continue

                    s = PecasOsSerializer(obj, data=item, partial=True, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    s.save()
                    resposta['editados'].append(s.data)

                # REMOVER
                for item in remover:
                    required = ['peca_item', 'peca_os', 'peca_empr', 'peca_fili']
                    if not all(k in item for k in required):
                        raise ValidationError("Campos obrigatórios para remover faltando.")

                    PecasOs.objects.using(banco).filter(
                        peca_item=item['peca_item'],
                        peca_os=item['peca_os'],
                        peca_empr=item['peca_empr'],
                        peca_fili=item['peca_fili']
                    ).delete()

                    resposta['removidos'].append(item['peca_item'])

            return Response(resposta)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({"error": str(e)}, status=400)



class ServicosOsViewSet(BaseMultiDBModelViewSet):
    serializer_class = ServicosOsSerializer
    parser_classes = [JSONParser]

    # ---- UTILIDADES ----
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
            logger.error(f"Ordem de serviço não encontrada para recalcular: {serv_os}")

    # ---- QUERYSET ----
    def get_queryset(self):
        banco = self.get_banco()

        serv_empr = self.request.query_params.get("serv_empr")
        serv_fili = self.request.query_params.get("serv_fili")
        serv_os = self.request.query_params.get("serv_os")

        if not all([serv_empr, serv_fili, serv_os]):
            logger.warning("Parâmetros obrigatórios faltando (serv_empr, serv_fili, serv_os)")
            return ServicosOs.objects.none()

        qs = ServicosOs.objects.using(banco).filter(
            serv_empr=serv_empr,
            serv_fili=serv_fili,
            serv_os=serv_os
        )

        return qs.order_by("serv_item")

    # ---- GET OBJECT ----
    def get_object(self):
        banco = self.get_banco()

        serv_item = self.kwargs.get("pk")
        serv_os = self.request.query_params.get("serv_os")
        serv_empr = self.request.query_params.get("serv_empr")
        serv_fili = self.request.query_params.get("serv_fili")

        if not all([serv_item, serv_os, serv_empr, serv_fili]):
            raise ValidationError("Campos serv_os, serv_empr, serv_fili e pk (serv_item) são obrigatórios.")

        try:
            return self.get_queryset().get(
                serv_item=serv_item,
                serv_os=serv_os,
                serv_empr=serv_empr,
                serv_fili=serv_fili
            )
        except ServicosOs.DoesNotExist:
            raise NotFound("Serviço não encontrado na lista especificada.")
        except ServicosOs.MultipleObjectsReturned:
            raise ValidationError("Mais de um serviço encontrado com essa chave composta.")

    # ---- CONTEXT ----
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    # ---- CREATE ----
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        try:
            is_many = isinstance(request.data, list)
            serializer = self.get_serializer(data=request.data, many=is_many)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic(using=banco):
                objs = serializer.save()

            exemplo = request.data[0] if is_many else request.data

            self.atualizar_total_ordem(
                exemplo.get('serv_empr'),
                exemplo.get('serv_fili'),
                exemplo.get('serv_os')
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except IntegrityError:
            return Response({'detail': 'Erro de integridade.'}, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({'detail': str(e)}, status=500)

    # ---- UPDATE ----
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.serv_empr,
                instance.serv_fili,
                instance.serv_os
            )
        return response

    # ---- DELETE ----
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.serv_empr, instance.serv_fili, instance.serv_os
        response = super().destroy(request, *args, **kwargs)

        if response.status_code == 204:
            self.atualizar_total_ordem(empr, fili, orde)

        return response

    # ---- UPDATE LISTA (LOTE) ----
    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request):
        banco = self.get_banco()
        data = request.data

        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):

                # ADICIONAR
                for item in adicionar:
                    obrig = ['serv_os', 'serv_empr', 'serv_fili', 'serv_serv']
                    faltando = [c for c in obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Faltam campos: {', '.join(faltando)}")

                    item['serv_item'] = get_next_service_id(
                        banco,
                        item['serv_os'],
                        item['serv_empr'],
                        item['serv_fili']
                    )

                    s = ServicosOsSerializer(data=item, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    obj = s.save()

                    resposta['adicionados'].append(
                        ServicosOsSerializer(obj, context={'banco': banco}).data
                    )

                # EDITAR
                for item in editar:
                    obrig = ['serv_item', 'serv_os', 'serv_empr', 'serv_fili']
                    if not all(k in item for k in obrig):
                        raise ValidationError("Campos obrigatórios para edição faltando.")

                    try:
                        obj = ServicosOs.objects.using(banco).get(
                            serv_item=item['serv_item'],
                            serv_os=item['serv_os'],
                            serv_empr=item['serv_empr'],
                            serv_fili=item['serv_fili']
                        )
                    except ServicosOs.DoesNotExist:
                        continue

                    s = ServicosOsSerializer(obj, data=item, partial=True, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    s.save()
                    resposta['editados'].append(s.data)

                # REMOVER
                for item in remover:
                    obrig = ['serv_item', 'serv_os', 'serv_empr', 'serv_fili']
                    if not all(k in item for k in obrig):
                        raise ValidationError("Campos obrigatórios para remover faltando.")

                    ServicosOs.objects.using(banco).filter(
                        serv_item=item['serv_item'],
                        serv_os=item['serv_os'],
                        serv_empr=item['serv_empr'],
                        serv_fili=item['serv_fili']
                    ).delete()

                    resposta['removidos'].append(item['serv_item'])

            return Response(resposta)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({"error": str(e)}, status=400)



class OsHoraViewSet(BaseMultiDBModelViewSet):
    serializer_class = OsHoraSerializer
    parser_classes = [JSONParser]

    def get_queryset(self):
        banco = self.get_banco()
        
        os_hora_empr = self.request.query_params.get('os_hora_empr')
        os_hora_fili = self.request.query_params.get('os_hora_fili')
        os_hora_os = self.request.query_params.get('os_hora_os')
        
        if not all([os_hora_empr, os_hora_fili, os_hora_os]):
            logger.warning("Parâmetros obrigatórios faltando para OsHora")
            return OsHora.objects.none()
        
        return OsHora.objects.using(banco).filter(
            os_hora_empr=os_hora_empr,
            os_hora_fili=os_hora_fili,
            os_hora_os=os_hora_os
        ).order_by('os_hora_data', 'os_hora_item')
    
    def get_object(self):
        banco = self.get_banco()
        
        os_hora_item = self.kwargs.get('pk')
        os_hora_os = self.request.query_params.get('os_hora_os')
        os_hora_empr = self.request.query_params.get('os_hora_empr')
        os_hora_fili = self.request.query_params.get('os_hora_fili')
        
        if not all([os_hora_item, os_hora_os, os_hora_empr, os_hora_fili]):
            raise ValidationError("Parâmetros obrigatórios faltando")
        
        try:
            return OsHora.objects.using(banco).get(
                os_hora_item=os_hora_item,
                os_hora_os=os_hora_os,
                os_hora_empr=os_hora_empr,
                os_hora_fili=os_hora_fili
            )
        except OsHora.DoesNotExist:
            raise NotFound("Registro de horas não encontrado")
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        
        try:
            is_many = isinstance(request.data, list)
            data_copy = request.data.copy() if not is_many else [item.copy() for item in request.data]
            
            # Gerar os_hora_item automaticamente
            if is_many:
                for item in data_copy:
                    if not item.get('os_hora_item'):
                        item['os_hora_item'] = self._get_next_item_number(
                            banco,
                            item['os_hora_os'],
                            item['os_hora_empr'],
                            item['os_hora_fili']
                        )
            else:
                if not data_copy.get('os_hora_item'):
                    data_copy['os_hora_item'] = self._get_next_item_number(
                        banco,
                        data_copy['os_hora_os'],
                        data_copy['os_hora_empr'],
                        data_copy['os_hora_fili']
                    )
            
            serializer = self.get_serializer(data=data_copy, many=is_many)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic(using=banco):
                serializer.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(f"Erro ao criar registro de horas: {str(e)}")
            return Response({'detail': str(e)}, status=500)
    
    def _get_next_item_number(self, banco, os_os, os_empr, os_fili):
        """Gera próximo número de item"""
        ultimo = OsHora.objects.using(banco).filter(
            os_hora_os=os_os,
            os_hora_empr=os_empr,
            os_hora_fili=os_fili
        ).aggregate(Max('os_hora_item'))['os_hora_item__max']
        return (ultimo or 0) + 1
    
    @action(detail=False, methods=['get'], url_path='total-horas')
    def total_horas(self, request, slug=None):
        """Retorna total de horas trabalhadas na OS"""
        banco = self.get_banco()
        
        os_hora_os = request.query_params.get('os_hora_os')
        os_hora_empr = request.query_params.get('os_hora_empr')
        os_hora_fili = request.query_params.get('os_hora_fili')
        
        if not all([os_hora_os, os_hora_empr, os_hora_fili]):
            return Response(
                {'error': 'Parâmetros obrigatórios faltando'},
                status=400
            )
        
        registros = OsHora.objects.using(banco).filter(
            os_hora_os=os_hora_os,
            os_hora_empr=os_hora_empr,
            os_hora_fili=os_hora_fili
        )
        
        # Calcula total usando o método do serializer
        total = 0.0
        for registro in registros:
            serializer = OsHoraSerializer(registro, context={'banco': banco})
            total += serializer.data.get('total_horas', 0)
        
        return Response({
            'total_horas': round(total, 2),
            'total_registros': registros.count()
        })
    
    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        """Atualização em lote de registros de horas"""
        banco = self.get_banco()
        data = request.data

        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):

                # ADICIONAR
                for item in adicionar:
                    obrig = ['os_hora_os', 'os_hora_empr', 'os_hora_fili', 'os_hora_data']
                    faltando = [c for c in obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Faltam campos: {', '.join(faltando)}")

                    if not item.get('os_hora_item'):
                        item['os_hora_item'] = self._get_next_item_number(
                            banco,
                            item['os_hora_os'],
                            item['os_hora_empr'],
                            item['os_hora_fili']
                        )

                    s = OsHoraSerializer(data=item, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    obj = s.save()

                    resposta['adicionados'].append(
                        OsHoraSerializer(obj, context={'banco': banco}).data
                    )

                # EDITAR
                for item in editar:
                    obrig = ['os_hora_item', 'os_hora_os', 'os_hora_empr', 'os_hora_fili']
                    if not all(k in item for k in obrig):
                        raise ValidationError("Campos obrigatórios para edição faltando.")

                    try:
                        obj = OsHora.objects.using(banco).get(
                            os_hora_item=item['os_hora_item'],
                            os_hora_os=item['os_hora_os'],
                            os_hora_empr=item['os_hora_empr'],
                            os_hora_fili=item['os_hora_fili']
                        )
                    except OsHora.DoesNotExist:
                        continue

                    s = OsHoraSerializer(obj, data=item, partial=True, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    s.save()
                    resposta['editados'].append(s.data)

                # REMOVER
                for item in remover:
                    obrig = ['os_hora_item', 'os_hora_os', 'os_hora_empr', 'os_hora_fili']
                    if not all(k in item for k in obrig):
                        raise ValidationError("Campos obrigatórios para remover faltando.")

                    OsHora.objects.using(banco).filter(
                        os_hora_item=item['os_hora_item'],
                        os_hora_os=item['os_hora_os'],
                        os_hora_empr=item['os_hora_empr'],
                        os_hora_fili=item['os_hora_fili']
                    ).delete()

                    resposta['removidos'].append(item['os_hora_item'])

            return Response(resposta)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({"error": str(e)}, status=400)
