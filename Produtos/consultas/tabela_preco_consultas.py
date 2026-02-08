from ..models import Tabelaprecos

def obter_tabela_preco(banco, empresa, filial, produto_codigo):
    if not banco:
        return None
    return Tabelaprecos.objects.using(banco).filter(
        tabe_empr=empresa,
        tabe_fili=filial,
        tabe_prod=produto_codigo
    ).first()
