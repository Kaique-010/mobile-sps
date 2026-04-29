from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from Pisos.models import Pedidospisos
from Pisos.serializers import PedidospisosSerializer


class PedidoPisosWebFlowService:
    @staticmethod
    def criar(banco, payload, request=None):
        serializer = PedidospisosSerializer(data=payload, context={"banco": banco, "request": request})
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    @staticmethod
    def atualizar(banco, pedido_nume, payload, request=None):
        inst = Pedidospisos.objects.using(banco).get(pedi_nume=pedido_nume)
        serializer = PedidospisosSerializer(inst, data=payload, partial=False, context={"banco": banco, "request": request})
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    @staticmethod
    def normalizar_erro(exc):
        if isinstance(exc, (DRFValidationError, DjangoValidationError)):
            return getattr(exc, "detail", None) or getattr(exc, "message_dict", None) or str(exc)
        return str(exc)
