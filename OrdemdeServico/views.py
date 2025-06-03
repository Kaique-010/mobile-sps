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
from OrdemdeServico.utils import get_next_item_number_sequence
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


class OrdemServicoPecasViewSet(BaseMultiDBModelViewSet,ModelViewSet):
    serializer_class = OrdemServicoPecasSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
   

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        peca_empr = self.request.query_params.get('peca_empr')
        peca_fili = self.request.query_params.get('peca_fili')
        peca_orde = self.request.query_params.get('peca_orde')

        if not peca_orde:
            logger.warning("peca_orde não fornecido")
            return Ordemservicopecas.objects.none()

        queryset = Ordemservicopecas.objects.using(banco).filter(peca_orde=peca_orde)
        if peca_empr:
            queryset = queryset.filter(peca_empr=peca_empr)
        if peca_fili:
            queryset = queryset.filter(peca_fili=peca_fili)

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

                for item in adicionar:
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

                for item in editar:
                    try:
                        obj = Ordemservicopecas.objects.using(banco).get(
                            peca_empr=item['peca_empr'],
                            peca_fili=item['peca_fili'],
                            peca_orde=item['peca_orde'],
                            peca_id=item['peca_id'],
                        )
                    except Ordemservicopecas.DoesNotExist:
                        continue

                    serializer = OrdemServicoPecasSerializer(obj, data=item, context={'banco': banco}, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    resposta['editados'].append(serializer.data)

                for item in remover:
                    Ordemservicopecas.objects.using(banco).filter(
                        peca_empr=item['peca_empr'],
                        peca_fili=item['peca_fili'],
                        peca_orde=item['peca_orde'],
                        peca_id=item['peca_id'],
                    ).delete()
                    resposta['removidos'].append(item['peca_id'])

            return Response(resposta)

        except Exception as e:
            logger.error(f"Erro ao processar update_lista: {str(e)}")
            return Response({"error": str(e)}, status=400)



class OrdemServicoServicosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = OrdemServicoServicosSerializer

    def get_queryset(self):
        banco = self.get_banco()
        ordem_id = self.request.query_params.get('ordem')
        qs = Ordemservicoservicos.objects.using(banco).all()
        return qs.filter(serv_orde=ordem_id) if ordem_id else qs

    def perform_create(self, serializer):
        banco = self.get_banco()
        ordem_id = serializer.validated_data.get('serv_orde')
        if not ordem_id:
            raise ValidationError("O campo 'serv_orde' é obrigatório.")
        
        with transaction.atomic(using=banco):
            ultimo = Ordemservicoservicos.objects.using(banco).filter(serv_orde=ordem_id).select_for_update().aggregate(Max('serv_id'))['serv_id__max'] or 0
            serializer.save(serv_id=ultimo + 1)


class ImagemAntesViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = ImagemAntesSerializer

    def get_queryset(self):
        return Ordemservicoimgantes.objects.using(self.get_banco()).all()


class ImagemDuranteViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = ImagemDuranteSerializer

    def get_queryset(self):
        return Ordemservicoimgdurante.objects.using(self.get_banco()).all()


class ImagemDepoisViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = ImagemDepoisSerializer

    def get_queryset(self):
        return Ordemservicoimgdepois.objects.using(self.get_banco()).all()