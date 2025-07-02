from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status
from .models import ComissaoSps
from .serializers import ComissaoSpsSerializer
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class ComissaoSpsViewSet(ModuloRequeridoMixin, ModelViewSet):
    modulo = 'comissoes'
    queryset = ComissaoSps.objects.all()
    serializer_class = ComissaoSpsSerializer

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return ComissaoSps.objects.using(banco).all()

    def get_serializer_class(self):
        return ComissaoSpsSerializer

    def perform_create(self, serializer):
        banco = get_licenca_db_config(self.request) or 'default'
        serializer.save()

    def perform_update(self, serializer):
        banco = get_licenca_db_config(self.request) or 'default'
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request) or 'default'
        instance = self.get_object()

        prefixos = {
            '1': 'MEL', '2': 'IMP', '3': 'DAS', '4': 'MOB', '5': 'VEN'
        }
        prefixo = prefixos.get(instance.comi_cate, 'UNK')
        codigo_base = f"{prefixo}{str(instance.comi_id).zfill(2)}"

        try:
            if Titulosreceber.objects.using(banco).filter(
                titu_titu__startswith=codigo_base,
                titu_aber__in=['P', 'T']
            ).exists():
                raise ValidationError("Existem títulos a receber pagos (total/parcial). Exclusão bloqueada.")

            if Titulospagar.objects.using(banco).filter(
                titu_titu__startswith=codigo_base,
                titu_aber__in=['P', 'T']
            ).exists():
                raise ValidationError("Existem títulos a pagar pagos (total/parcial). Exclusão bloqueada.")

            with transaction.atomic(using=banco):
                Titulosreceber.objects.using(banco).filter(
                    titu_titu__startswith=codigo_base
                ).delete()

                Titulospagar.objects.using(banco).filter(
                    titu_titu__startswith=codigo_base
                ).delete()

                instance.delete(using=banco)
                logger.info(f"Comissão {instance.comi_id} e títulos excluídos com sucesso.")
                return Response(status=status.HTTP_204_NO_CONTENT)

        except ValidationError as e:
            logger.warning(f"Exclusão bloqueada: {e.detail}")
            return Response({'erro': str(e.detail)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Erro ao excluir comissão {instance.comi_id}: {str(e)}")
            return Response({'erro': 'Erro interno ao excluir comissão.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
