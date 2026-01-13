# notas_fiscais/handlers/itens_handler.py

from django.core.exceptions import ValidationError

class ItensHandler:

    @staticmethod
    def validar_itens(itens):
        """
        Verifica integridade dos itens antes de enviar ao service.
        """
        if not itens or len(itens) == 0:
            raise ValidationError("A nota precisa ter pelo menos um item.")

        for i, item in enumerate(itens):
            if float(item.get("quantidade", 0)) <= 0:
                raise ValidationError(f"Item {i+1}: quantidade inválida.")

            val = float(item.get("unitario") or item.get("valor_unit") or 0)
            if val <= 0:
                raise ValidationError(f"Item {i+1}: valor unitário inválido.")

            if "produto" not in item and "codigo" not in item:
                raise ValidationError(f"Item {i+1}: produto obrigatório.")

        return True


    @staticmethod
    def normalizar_item(item):
        """
        Padroniza o item.
        """
        item = item.copy()

        # Aliases
        if "valor_unit" in item and "unitario" not in item:
            item["unitario"] = item.pop("valor_unit")
        if "codigo" in item and "produto" not in item:
            item["produto"] = item.pop("codigo")

        # Converte tudo para número correto
        for campo in ["quantidade", "unitario", "desconto"]:
            if campo in item:
                item[campo] = float(item[campo])

        # Total calculado
        item["total"] = (item["quantidade"] * item["unitario"]) - item.get("desconto", 0)

        return item

    @staticmethod
    def normalizar_itens(lista):
        return [ItensHandler.normalizar_item(i) for i in lista]


    # -------- Impostos --------

    @staticmethod
    def normalizar_impostos(item_imposto):
        """
        Impostos opcionais. Se vier vazio, vira None.
        """
        if not item_imposto:
            return {}

        limpado = {}
        for k, v in item_imposto.items():
            if v in ("", None):
                limpado[k] = None
            else:
                limpado[k] = float(v)

        return limpado
