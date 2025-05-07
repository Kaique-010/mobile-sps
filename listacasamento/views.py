# views.py
from rest_framework import viewsets
from rest_framework.viewsets import ModelViewSet
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
from Produtos.models import Produtos
from rest_framework.exceptions import NotFound
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
    lookup_field = 'item_item'

    def get_queryset(self):
        item_empr = self.request.query_params.get('item_empr')
        item_fili = self.request.query_params.get('item_fili')
        item_list = self.request.query_params.get('item_list')

        logger.info(f"Parâmetros recebidos: item_empr={item_empr}, item_fili={item_fili}, item_list={item_list}")

        # Verifica se algum parâmetro obrigatório está ausente
        if None in (item_empr, item_fili, item_list):
            logger.warning("Parâmetros obrigatórios faltando")
            raise ValidationError({"detail": "item_empr, item_fili e item_list são obrigatórios."})

        # Filtra os itens pela combinação de parâmetros
        return ItensListaCasamento.objects.filter(
            item_empr=item_empr,
            item_fili=item_fili,
            item_list=item_list
        )


    def get_object(self):
        queryset = self.get_queryset()
        pk = self.kwargs.get(self.lookup_field)

        item_list = self.request.query_params.get("item_list")
        item_empr = self.request.query_params.get("item_empr")
        item_fili = self.request.query_params.get("item_fili")

        if not all([item_list, item_empr, item_fili]):
            raise ValidationError("Parâmetros item_list, item_empr e item_fili são obrigatórios.")

        instance = queryset.filter(
            pk=pk,
            item_list=item_list,
            item_empr=item_empr,
            item_fili=item_fili
        ).first()

        if not instance:
            raise NotFound("Item não encontrado na lista especificada.")

        return instance



    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            logger.info(f"Criação de item(s) por {request.user.pk if request.user else 'Anon'}")

            # Validação: Garantir que item_pedi seja 0 para todos os itens
            for item in request.data:
                if item.get('item_pedi') != 0:
                    return Response({"detail": "Item não pode ser criado com item_pedi diferente de 0."}, status=400)

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

    @action(detail=False, methods=["delete"], url_path="delete-by-composite-key")
    def delete_by_composite_key(self, request):
        item_empr = request.query_params.get("item_empr")
        item_fili = request.query_params.get("item_fili")
        item_list = request.query_params.get("item_list")
        item_item = request.query_params.get("item_item")

        if not all([item_empr, item_fili, item_list, item_item]):
            return Response({"detail": "Parâmetros obrigatórios faltando."}, status=400)

        try:
            item = ItensListaCasamento.objects.get(
                item_empr=item_empr,
                item_fili=item_fili,
                item_list=item_list,
                item_item=item_item
            )
        except ItensListaCasamento.DoesNotExist:
            return Response({"detail": "Item não encontrado."}, status=404)

        if item.item_pedi != 0:
            return Response({"detail": "Item já foi pedido e não pode ser excluído."}, status=400)

        item.delete()
        return Response(status=204)





    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Verifica se o item foi pedido (não pode editar)
        if instance.item_pedi != 0:
            return Response({"detail": "Item já foi pedido e não pode ser editado."}, status=400)

        return super().update(request, *args, **kwargs)
