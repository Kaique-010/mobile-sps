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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            if isinstance(request.data, list):
                serializer = self.get_serializer(data=request.data, many=True)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return super().create(request, *args, **kwargs)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response({'detail': 'Erro de integridade no banco de dados.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_object(self):
        item_item = self.kwargs.get(self.lookup_field)
        lista_id = self.request.query_params.get("lista_id")

        if not lista_id:
            raise ValidationError({"detail": "Parâmetro 'lista_id' é obrigatório na URL para identificar o item corretamente."})

        try:
            return ItensListaCasamento.objects.get(
                item_item=int(item_item),
                item_list=int(lista_id)
            )
        except ItensListaCasamento.DoesNotExist:
            raise NotFound("Item não encontrado na lista especificada.")
        except ItensListaCasamento.MultipleObjectsReturned:
            raise ValidationError({"detail": "Mais de um item com esse código nesta lista. Verifique integridade dos dados."})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()  # Obtém o item filtrado por lista
        if instance.item_pedi != 0:
            return Response({"detail": "Item já foi pedido e não pode ser excluído."}, status=400)

        self.perform_destroy(instance)  # Exclui o item
        
        # Verificar se o item foi excluído antes de retornar a resposta
        if not ItensListaCasamento.objects.filter(id=instance.id).exists():
            return Response(status=204)
        else:
            return Response({"detail": "Erro na exclusão do item."}, status=500)


    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.item_pedi != 0:
            return Response(
                {"detail": "Este item já foi pedido e não pode ser editado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)
