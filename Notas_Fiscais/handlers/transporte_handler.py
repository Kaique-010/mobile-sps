from django.core.exceptions import ValidationError

class TransporteHandler:

    @staticmethod
    def normalizar(data):
        data = data.copy()

        # Placa sempre maiúscula
        if data.get("placa_veiculo"):
            data["placa_veiculo"] = data["placa_veiculo"].upper()

        # UF não pode vir com espaço
        if data.get("uf_veiculo"):
            data["uf_veiculo"] = data["uf_veiculo"].strip().upper()

        return data

    @staticmethod
    def validar(data):
        # Sem validação pesada aqui, SEFAZ valida depois
        return True
