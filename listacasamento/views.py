from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from django.db import transaction, IntegrityError
from rest_framework.decorators import api_view
from .models import ListaCasamento, ItensListaCasamento
from .serializers import ListaCasamentoSerializer, ItensListaCasamentoSerializer

import logging
logger = logging.getLogger(__name__)


class ListaCasamentoViewSet(ModelViewSet):
    serializer_class = ListaCasamentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['list_noiv__nome', 'list_codi']

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', 'default')
        return ListaCasamento.objects.using(db_alias).all().order_by('list_codi')


class ItensListaCasamentoViewSet(ModelViewSet):
    serializer_class = ItensListaCasamentoSerializer

    def get_queryset(self):
        item_empr = self.request.query_params.get('item_empr')
        item_fili = self.request.query_params.get('item_fili')
        item_list = self.request.query_params.get('item_list')

        logger.info(f"Parâmetros recebidos: item_empr={item_empr}, item_fili={item_fili}, item_list={item_list}")

        if None in (item_empr, item_fili, item_list):
            logger.warning("Parâmetros obrigatórios faltando")
            raise ValidationError({"detail": "item_empr, item_fili e item_list são obrigatórios."})

        return ItensListaCasamento.objects.filter(
            item_empr=item_empr,
            item_fili=item_fili,
            item_list=item_list
        )

    def get_object(self):
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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            logger.info(f"Criação de item(s) por {request.user.pk if request.user else 'None'}")

            for item in request.data if isinstance(request.data, list) else [request.data]:
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


    @api_view(["POST"])
    def update_lista(request):
        # Dados que serão passados
        remover = request.data.get("remover", [])
        adicionar = request.data.get("adicionar", [])

        # Remover os itens
        for item in remover:
            ItensListaCasamento.objects.filter(
                item_empr=item["item_empr"],
                item_fili=item["item_fili"],
                item_list=item["item_list"],
                item_item=item["item_item"]
            ).delete()

        # Adicionar os novos itens
        for item in adicionar:
            ItensListaCasamento.objects.create(**item)

        return Response({"message": "Lista atualizada com sucesso!"})

   