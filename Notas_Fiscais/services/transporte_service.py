# notas_fiscais/services/transporte_service.py

from ..models import Transporte
from ..handlers.transporte_handler import TransporteHandler


class TransporteService:

    @staticmethod
    def definir(nota, data):
        data = TransporteHandler.normalizar(data)
        TransporteHandler.validar(data)

        # update_or_create para simplicidade
        Transporte.objects.update_or_create(
            nota=nota,
            defaults=data
        )
