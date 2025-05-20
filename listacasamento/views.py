from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from django.db import transaction, IntegrityError
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from .models import ListaCasamento, ItensListaCasamento
from .serializers import ListaCasamentoSerializer, ItensListaCasamentoSerializer

import logging
logger = logging.getLogger(__name__)


class ListaCasamentoViewSet(ModuloRequeridoMixin,ModelViewSet):
    modulo_necessario = 'listacasamento'
    permission_classes = [IsAuthenticated]
    serializer_class = ListaCasamentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['list_noiv__nome', 'list_codi']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if banco:
            return ListaCasamento.objects.using(banco).all().order_by('list_codi')
        
        else:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
    
    def destroy(self, request, *args, **kwargs):
        lista = self.get_object()
        banco = get_licenca_db_config(self.request)
        
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        # Verifica se tem itens antes de excluir
        if ItensListaCasamento.objects.using(banco).filter(
            item_empr=lista.list_empr,
            item_fili=lista.list_fili,
            item_list=lista.list_codi
        ).exists():
            return Response(
                {"detail": "Não é possível excluir a lista de casamento, pois existem itens associados."},
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

    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        remover = data.get("remover", [])
        adicionar = data.get("adicionar", [])

        try:
            with transaction.atomic(using=banco):
                # Remover itens
                for item in remover:
                    ItensListaCasamento.objects.using(banco).filter(
                        item_empr=item["item_empr"],
                        item_fili=item["item_fili"],
                        item_list=item["item_list"],
                        item_item=item["item_item"]
                    ).delete()

                # Ajustar dados para adicionar
                for item in adicionar:
                    item["item_prod"] = item.pop("prod_codi")
                    item["item_pedi"] = 0

                serializer = self.get_serializer(data=adicionar, many=True)
                serializer.is_valid(raise_exception=True)

                # Cria manualmente no banco correto
                for validated_data in serializer.validated_data:
                    ItensListaCasamento.objects.using(banco).create(**validated_data)

        except serializers.ValidationError as e:
            logger.warning(f"Erros de validação: {e.detail}")
            return Response({"errors": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response({'detail': 'Erro de integridade.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erro inesperado: {str(e)}")
            return Response({'detail': 'Erro interno no servidor.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Lista atualizada com sucesso!"})
