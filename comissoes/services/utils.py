from decimal import Decimal, ROUND_HALF_UP


def decimal_2(valor) -> Decimal:
    if valor is None:
        return Decimal("0.00")
    if isinstance(valor, Decimal):
        v = valor
    else:
        v = Decimal(str(valor))
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
