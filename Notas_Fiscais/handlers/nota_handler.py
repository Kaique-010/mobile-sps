# notas_fiscais/handlers/nota_handler.py

from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError


class NotaHandler:

    @staticmethod
    def preparar_criacao(data, empresa, filial):
        """
        Prepara dados da nota com base na empresa/filial da sessão.
        """

        data = data.copy()
        # Remove campos que não pertencem ao modelo Nota
        data.pop("itens", None)
        data.pop("impostos", None)
        data.pop("transporte", None)

        data["empresa"] = empresa
        data["filial"] = filial

        # Emitente sempre é a filial da sessão
        data["emitente"] = filial

        # Normalização de defaults
        if not data.get("data_emissao"):
            data["data_emissao"] = timezone.now().date()

        return data
