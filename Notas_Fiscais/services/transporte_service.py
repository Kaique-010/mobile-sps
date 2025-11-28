# notas_fiscais/services/transporte_service.py

from ..models import Transporte
from Entidades.models import Entidades
from ..handlers.transporte_handler import TransporteHandler


class TransporteService:

    @staticmethod
    def definir(nota, data):
        data = TransporteHandler.normalizar(data)
        TransporteHandler.validar(data)

        banco = getattr(nota._state, 'db', 'default')
        transp_id = data.get('transportadora')
        if transp_id and not isinstance(transp_id, Entidades):
            ent = (
                Entidades.objects.using(banco)
                .filter(enti_empr=nota.empresa, enti_clie=int(transp_id))
                .first()
            )
            data['transportadora'] = ent

        # update_or_create para simplicidade
        Transporte.objects.update_or_create(
            nota=nota,
            defaults=data
        )
