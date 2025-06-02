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
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        remover = data.get('remover', [])
        adicionar = data.get('adicionar', [])

        try:
            with transaction.atomic(using=banco):
                if remover:
                    Ordemservicopecas.objects.using(banco).filter(
                        peca_empr=remover[0].get('peca_empr'),
                        peca_fili=remover[0].get('peca_fili'),
                        peca_orde=remover[0].get('peca_orde'),
                        peca_id__in=[x.get('peca_id') for x in remover]
                    ).delete()

                if adicionar:
                    # Pega o último peca_id para aquela ordem, empresa e filial
                    peca_empr = adicionar[0].get('peca_empr')
                    peca_fili = adicionar[0].get('peca_fili')
                    peca_orde = adicionar[0].get('peca_orde')

                    ultimo_id = get_next_item_number(peca_empr, peca_fili, peca_orde, banco) - 1

                    for i, peca in enumerate(adicionar):
                        # Remove campos extras que não pertencem ao modelo
                        for campo_extra in [
                            'prod_nome', 'precos', 'saldo_estoque', 'imagem_base64',
                            'prod_empr', 'prod_loca', 'prod_ncm', 'prod_coba', 'prod_foto',
                            'prod_unme', 'prod_grup', 'prod_sugr', 'prod_fami', 'prod_marc'
                        ]:
                            peca.pop(campo_extra, None)

                        # Força o peca_id incremental, ignorando o que vier no front
                        peca['peca_id'] = ultimo_id + i + 1

                        # Ajuste do nome do campo, se necessário
                        if 'prod_codi' in peca:
                            peca['peca_codi'] = peca.pop('prod_codi')

                        serializer = OrdemServicoPecasSerializer(data=peca, context={'banco': banco})
                        if serializer.is_valid():
                            try:
                                serializer.save()
                            except IntegrityError as e:
                                logger.exception(f"Erro de integridade ao salvar peça: {peca}")
                                return Response({"detail": str(e)}, status=500)
                        else:
                            logger.error(f"Erro de validação: {serializer.errors} | Dados: {peca}")
                            return Response(serializer.errors, status=400)

        except IntegrityError as e:
            logger.exception(f"Erro de integridade ao salvar peça. Dados: {request.data}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True}, status=status.HTTP_200_OK)





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