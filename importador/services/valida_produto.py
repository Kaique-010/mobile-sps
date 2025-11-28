# importador_produtos/services/valida_produto.py
class ValidadorProduto:
    def __init__(self, row):
        self.row = row

    def validar(self):
        if not self.row.get("prod_nome"):
            raise ValueError("Produto sem nome")

        if not self.row.get("prod_unme"):
            raise ValueError("Unidade inválida")

        if not self.row.get("prod_ncm"):
            raise ValueError("NCM inválido")

        return True
