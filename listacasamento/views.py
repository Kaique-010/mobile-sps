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

    def create(self, request, *args, **kwargs):
        try:
            if isinstance(request.data, list):
                serializer = self.get_serializer(data=request.data, many=True)
                serializer.is_valid(raise_exception=True)

                # Cria os objetos manualmente a partir dos dados validados
                items = [ItensListaCasamento(**data) for data in serializer.validated_data]
                created_items = ItensListaCasamento.objects.bulk_create(items)

                # Re-serializa os objetos criados para retorno
                response_serializer = self.get_serializer(created_items, many=True)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

            # Se não for lista, salva normalmente
            return super().create(request, *args, **kwargs)

        except ValidationError as e:
            print(f'🧨 ValidationError: {e.detail}')
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except IntegrityError as e:
            print(f'🧱 IntegrityError: {str(e)}')
            return Response({'detail': 'Erro de integridade no banco de dados.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f'🔥 Erro inesperado: {str(e)}')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)