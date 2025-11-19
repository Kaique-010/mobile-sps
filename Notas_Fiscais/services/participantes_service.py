# notas_fiscais/services/participantes_service.py

from ..models import Emitente, Destinatario
from ..handlers.participantes_handler import ParticipantesHandler


class ParticipantesService:

    @staticmethod
    def criar_emitente(data):
        ParticipantesHandler.validar_emitente(data)
        data = ParticipantesHandler.normalizar_emitente(data)
        return Emitente.objects.create(**data)

    @staticmethod
    def criar_destinatario(data):
        ParticipantesHandler.validar_destinatario(data)
        data = ParticipantesHandler.normalizar_destinatario(data)
        return Destinatario.objects.create(**data)
