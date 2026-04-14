# importador_produtos/services/mapeamento_campos.py
import re
from .base_alias import BASE_ALIAS

EXTRA_ALIAS = {
    "cod prod": "prod_codi",
    "cd prod": "prod_codi",
    "descricao do item": "prod_nome",
    "descricao item": "prod_nome",
    "desc item": "prod_nome",
    "nome do produto": "prod_nome",
    "codigo de barras": "prod_gtin",
    "sub cat": "prod_sugr",
    "orig": "prod_orig_merc",
    "valor venda": "preco",
    "pr venda": "preco",
    "prc venda": "preco",
    "preco unitario": "preco",
    "preco venda r": "preco",
    "preco venda r$": "preco",
    "preco compra": "preco_compra",
    "preco custo": "preco_compra",
    "custo geral": "preco_compra",
    "cuge": "preco_compra",
    "cugeral": "preco_compra",
    "preco a vista": "preco_vista",
    "preco avista": "preco_vista",
    "a vista": "preco_vista",
    "avista": "preco_vista",
    "avis": "preco_vista",
    "preco a prazo": "preco_prazo",
    "a prazo": "preco_prazo",
    "apra": "preco_prazo",
}

class MapeamentoCampos:
    def __init__(self, df):
        self.df = df
        self.alias = {**BASE_ALIAS, **EXTRA_ALIAS}

    def normalizar(self, col):
        import unicodedata
        x = str(col).strip().lower()
        x = unicodedata.normalize('NFKD', x)
        x = ''.join(c for c in x if not unicodedata.combining(c))
        x = re.sub(r'[^a-z0-9 ]', '', x)
        return x

    def map_coluna(self, col):
        norm = self.normalizar(col)
        return self.alias.get(norm, norm)

    def mapear(self):
        novas = []
        contagem = {}
        for col in self.df.columns:
            nome = self.map_coluna(col)
            contagem[nome] = contagem.get(nome, 0) + 1
            if contagem[nome] > 1:
                nome = f"{nome}__{contagem[nome]}"
            novas.append(nome)
        self.df.columns = novas
        return self.df
