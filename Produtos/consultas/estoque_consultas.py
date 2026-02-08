from ..models import SaldoProduto

def obter_saldo_produto(banco, empresa, filial, produto_codigo):
    if not banco:
        return None
    return SaldoProduto.objects.using(banco).filter(
        empresa=empresa,
        filial=filial,
        produto_codigo=produto_codigo
    ).first()
