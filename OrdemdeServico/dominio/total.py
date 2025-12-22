from .excecoes import ErroDominio

class CalculadoraTotal:
    """
    Regra de cálculo de total.
    """

    def calcular(self, itens):
        total = sum(item["valor"] for item in itens)
        if total < 0:
            raise ErroDominio("Total negativo não é permitido")
        return total
