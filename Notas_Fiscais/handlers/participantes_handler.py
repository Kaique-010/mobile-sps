# notas_fiscais/handlers/participantes_handler.py

from django.core.exceptions import ValidationError

class ParticipantesHandler:

    @staticmethod
    def validar_emitente(data):
        if not data.get("cnpj"):
            raise ValidationError("CNPJ do emitente é obrigatório.")

        return True

    @staticmethod
    def validar_destinatario(data):
        if not data.get("documento"):
            raise ValidationError("Documento do destinatário é obrigatório.")

        return True

    @staticmethod
    def normalizar_emitente(data):
        data = data.copy()
        data["cnpj"] = data["cnpj"].replace(".", "").replace("/", "").replace("-", "")
        return data

    @staticmethod
    def normalizar_destinatario(data):
        data = data.copy()
        data["documento"] = data["documento"].replace(".", "").replace("-", "")
        return data
