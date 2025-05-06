# views.py
from rest_framework import viewsets
from rest_framework.viewsets import ModelViewSet
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
from Produtos.models import Produtos
from rest_framework.response import Response
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from .models import ListaCasamento, ItensListaCasamento
from django.db import models
from rest_framework.decorators import action
from .serializers import ListaCasamentoSerializer, ItensListaCasamentoSerializer


import logging
logger = logging.getLogger(__name__)  
class ListaCasamentoViewSet(viewsets.ModelViewSet):
    serializer_class = ListaCasamentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['list_noiv__nome', 'list_codi']

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', 'default')
        return ListaCasamento.objects.using(db_alias).all().order_by('list_codi')



class ItensListaCasamentoViewSet(viewsets.ModelViewSet):
    queryset = ItensListaCasamento.objects.all()
    serializer_class = ItensListaCasamentoSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        logger.debug("🔥 Entrou no método create de ItensListaCasamentoViewSet")

        try:
            if isinstance(request.data, list):
                serializer = self.get_serializer(data=request.data, many=True)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            # Se for objeto único
            return super().create(request, *args, **kwargs)

        except ValidationError as e:
            logger.warning(f'🧨 ValidationError: {e.detail}')
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except IntegrityError as e:
            logger.error(f'🧱 IntegrityError: {str(e)}')
            return Response({'detail': 'Erro de integridade no banco de dados.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("🔥 Erro inesperado ao salvar itens.")
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_object(self):
        queryset = self.get_queryset()
        item_empr = self.kwargs.get('item_empr')
        item_fili = self.kwargs.get('item_fili')
        item_item = self.kwargs.get('item_item')


        if not all([item_empr, item_fili, item_item]):
            raise ValidationError("Parâmetros são obrigatórios.")

        try:
            return queryset.get(
                item_empr=item_empr,
                item_fili=item_fili,
                item_item=item_item,
            )
        except MultipleObjectsReturned:
            raise ValidationError("Mais de um item encontrado com esses critérios.")
        except ItensListaCasamento.DoesNotExist:
            raise ValidationError("Item não encontrado.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        logger.debug(f"🎯 Tentando deletar item com item_item: {instance.item_item}, item_pedi: {instance.item_pedi}")

        if instance.item_pedi != 0:
            return Response({"detail": "Item já foi pedido e não pode ser excluído."}, status=400)

        self.perform_destroy(instance)
        return Response(status=204)


    def update(self, request, *args, **kwargs):
        instance = self.get_object()


        if instance.item_pedi != 0:
            logger.info(f"❌ Tentativa de editar item com pedido: {instance.item_item}")
            return Response(
                {"detail": "Este item já foi pedido e não pode ser editado."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Realiza a atualização do item
        return super().update(request, *args, **kwargs)
