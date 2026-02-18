from decimal import Decimal
from decimal import ROUND_DOWN, ROUND_HALF_UP

class RenegociacaoCalculadora:

    @staticmethod
    def consolidar(
        *,
        slug: str,
        valor_total: Decimal,
        juros: Decimal,
        multa: Decimal,
        desconto: Decimal,
    ):
        valor_final = valor_total + juros + multa - desconto
        return {
            "valor_original": valor_total,
            "valor_final": valor_final
        }

    @staticmethod
    def calcular_parcelas(
        *,
        slug: str,
        valor_final: Decimal,
        parcelas: int,
    ):
        total = Decimal(str(valor_final))
        n = int(parcelas or 1)
        if n <= 0:
            n = 1
        # Valor base truncado para 2 casas
        base = (total / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        soma_base = base * n
        resto = (total - soma_base).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # Distribui os centavos restantes nas primeiras parcelas
        centavos = int((resto * 100).to_integral_value(rounding=ROUND_HALF_UP))
        valores = [base for _ in range(n)]
        for i in range(centavos):
            valores[i] = (valores[i] + Decimal("0.01")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # Garantir soma exata
        ajuste = total - sum(valores)
        if ajuste != Decimal("0.00"):
            valores[-1] = (valores[-1] + ajuste).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return valores
