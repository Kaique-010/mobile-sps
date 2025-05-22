from rest_framework.viewsets import ModelViewSet
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db import transaction, IntegrityError, models

from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from .models import ListaCasamento, ItensListaCasamento
from .serializers import ListaCasamentoSerializer, ItensListaCasamentoSerializer

import logging
logger = logging.getLogger(__name__)


class ListaCasamentoViewSet(ModuloRequeridoMixin, ModelViewSet):
    modulo_necessario = 'listacasamento'
    permission_classes = [IsAuthenticated]
    serializer_class = ListaCasamentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['list_noiv__nome', 'list_codi']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if banco:
            return ListaCasamento.objects.using(banco).all().order_by('list_codi')
        logger.error("Banco de dados não encontrado.")
        raise NotFound("Banco de dados não encontrado.")

    def destroy(self, request, *args, **kwargs):
        lista = self.get_object()
        banco = get_licenca_db_config(self.request)

        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        if ItensListaCasamento.objects.using(banco).filter(
            item_empr=lista.list_empr,
            item_fili=lista.list_fili,
            item_list=lista.list_codi
        ).exists():
            return Response(
                {"detail": "Não é possível excluir a lista de casamento, Há itens associados."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic(using=banco):
            lista.delete()
            logger.info(f"🗑️ Exclusão da lista de casamento ID {lista.list_codi} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context


class ItensListaCasamentoViewSet(ModuloRequeridoMixin, ModelViewSet):
    modulo_necessario = 'listacasamento'
    serializer_class = ItensListaCasamentoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        item_empr = self.request.query_params.get('item_empr')
        item_fili = self.request.query_params.get('item_fili')
        item_list = self.request.query_params.get('item_list')

        if not item_list:
            logger.warning("item_list não fornecido")
            return ItensListaCasamento.objects.none()

        queryset = ItensListaCasamento.objects.using(banco).filter(item_list=item_list)
        if item_empr:
            queryset = queryset.filter(item_empr=item_empr)
        if item_fili:
            queryset = queryset.filter(item_fili=item_fili)

        logger.info(f"Parâmetros recebidos: item_empr={item_empr}, item_fili={item_fili}, item_list={item_list}")
        logger.info(f"Queryset filtrado: {queryset.query}")
        return queryset.order_by('item_item')

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        item_item = self.kwargs.get('pk')
        item_list = self.request.query_params.get("item_list")
        item_empr = self.request.query_params.get("item_empr")
        item_fili = self.request.query_params.get("item_fili")

        if not all([item_list, item_empr, item_fili, item_item]):
            raise ValidationError("Parâmetros item_list, item_empr, item_fili e pk (item_item) são obrigatórios.")

        try:
            return self.get_queryset().get(
                item_item=item_item,
                item_list=item_list,
                item_empr=item_empr,
                item_fili=item_fili
            )
        except ItensListaCasamento.DoesNotExist:
            raise NotFound("Item não encontrado na lista especificada.")
        except ItensListaCasamento.MultipleObjectsReturned:
            raise ValidationError("Mais de um item encontrado com essa chave composta.")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def destroy(self, request, *args, **kwargs):
        item = self.get_object()
        if item.item_pedi != 0:
            return Response({"detail": "Não é possível excluir item já associado a pedido."}, status=400)
        return super().destroy(request, *args, **kwargs)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            logger.info(f"Criação de item(s) por {request.user.pk if request.user else 'None'}")

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
                # Remover itens
                if remover:
                    # Você pode ajustar a query conforme seu modelo de exclusão
                    ItensListaCasamento.objects.using(banco).filter(
                        item_empr=remover[0].get('item_empr'),
                        item_fili=remover[0].get('item_fili'),
                        item_list=remover[0].get('item_list'),
                        item_item__in=[x.get('item_item') for x in remover]
                    ).delete()

                # Adicionar itens
                for item in adicionar:
                    
                  
                    
                    # Limpa campos extras que o serializer não aceita
                    for campo_extra in ['prod_nome', 'precos', 'saldo_estoque', 'imagem_base64', 'prod_empr', 'prod_loca', 'prod_ncm', 'prod_coba', 'prod_foto', 'prod_unme', 'prod_grup', 'prod_sugr', 'prod_fami', 'prod_marc']:
                        item.pop(campo_extra, None)
                    item.pop('item_item', None)
                    # Ajusta o campo ForeignKey para o serializer
                    if 'prod_codi' in item:
                        item['item_prod'] = item.pop('prod_codi')

                    serializer = ItensListaCasamentoSerializer(data=item, context={'banco': banco})
                    if serializer.is_valid():
                        serializer.save()
                    else:
                        logger.error(f"Erro ao salvar item {item}: {serializer.errors}")
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Itens atualizados com sucesso."})

        except Exception as e:
            logger.error(f"Erro ao atualizar lista: {e}")
            return Response({"detail": "Erro ao atualizar lista."}, status=status.HTTP_400_BAD_REQUEST)