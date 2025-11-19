# notas_fiscais/services/evento_service.py

from ..models import NotaEvento


class EventoService:

    @staticmethod
    def registrar(nota, tipo, descricao, xml=None, protocolo=None):
        return NotaEvento.objects.create(
            nota=nota,
            tipo=tipo,
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
        )
