from ..dominio.total import CalculadoraTotal

def atualizar_total(ordem_model, itens, banco):
    calculadora = CalculadoraTotal()
    total = calculadora.calcular(itens)

    ordem_model.orde_total = total
    ordem_model.save(using=banco, update_fields=["orde_total"])

    return total
