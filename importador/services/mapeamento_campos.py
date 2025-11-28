# importador_produtos/services/mapeamento_campos.py
import json
import os
import re
from .base_alias import BASE_ALIAS 

BASE_ALIAS = {
    # Código do produto
    "codigo": "prod_codi",
    "código": "prod_codi",
    "cod": "prod_codi",
    "cod prod": "prod_codi",
    "cd prod": "prod_codi",
    "prod_codigo": "prod_codi",
    "prod_cod": "prod_codi",
    "produto_codigo": "prod_codi",
    "produto_cod": "prod_codi",
    
    # Nome / descrição
    "produto": "prod_nome",
    "nome": "prod_nome",
    "descricao": "prod_nome",
    "descrição": "prod_nome",
    "descricao do item": "prod_nome",
    "descrição do item": "prod_nome",
    "descricao item": "prod_nome",
    "desc item": "prod_nome",
    "NOME DO PRODUTO": "prod_nome",
    "nome do produto": "prod_nome",
    "nome produto": "prod_nome",
    "nOME DO PRODUTO": "prod_nome",
    
    # NCM / classificação fiscal
    "ncm": "prod_ncm",
    "classificacao fiscal": "prod_ncm",
    "classificação fiscal": "prod_ncm",
    
    # GTIN / código de barras
    "gtin": "prod_gtin",
    "ean": "prod_gtin",
    "cod barras": "prod_gtin",
    "codigo de barras": "prod_gtin",
    
    # Marca / fabricante
    "marca": "prod_marc",
    "fabricante": "prod_marc",
    # Grupo / categoria
    "grupo": "prod_grup",
    "categoria": "prod_grup",
    
    # Subgrupo / subcategoria
    "subgrupo": "prod_sugr",
    "sub grupo": "prod_sugr",
    "sub cat": "prod_sugr",
    "subcategoria": "prod_sugr",
    
    # Família
    "família": "prod_fami",
    "familia": "prod_fami",
    "famili": "prod_fami",
    "familia": "prod_fami",
    
    # Unidade
    "unidade": "prod_unme",
    "un": "prod_unme",
    "unid": "prod_unme",
    "und": "prod_unme",
    "unidade medida": "prod_unme",
    "unidade de medida": "prod_unme",
    
    # Localização
    "local": "prod_loca",
    "localizacao": "prod_loca",
    "localização": "prod_loca",
    
    # Origem
    "origem": "prod_orig_merc",
    "orig": "prod_orig_merc",
    "origem mercadoria": "prod_orig_merc",
    "origem mercadoria": "prod_orig_merc",
    
    # Preço
    "preço": "preco",
    "preco": "preco",
    "valor": "preco",
    "valor venda": "preco",
    "pr venda": "preco",
    "prc venda": "preco",
    "preço venda": "preco",
    "preco venda": "preco",
    "preço venda r": "preco",
    "preco venda r": "preco",
    "preco venda r$": "preco",
    "preço venda r$": "preco",
    "preco unitario": "preco",
    "preço unitario": "preco",
    "preço unitário": "preco",
    "preco unitário": "preco",

    # Preço de compra / custo
    "preco compra": "preco_compra",
    "preço compra": "preco_compra",
    "custo": "preco_compra",
    "custo geral": "preco_compra",
    "cuge": "preco_compra",
    "cugeral": "preco_compra",
    "preco custo": "preco_compra",
    "preço custo": "preco_compra",

    # Preço à vista
    "preco vista": "preco_vista",
    "preço vista": "preco_vista",
    "preco a vista": "preco_vista",
    "preço a vista": "preco_vista",
    "preco avista": "preco_vista",
    "preço avista": "preco_vista",
    "avista": "preco_vista",
    "a vista": "preco_vista",
    "avis": "preco_vista",

    # Preço a prazo
    "preco prazo": "preco_prazo",
    "preço prazo": "preco_prazo",
    "preco a prazo": "preco_prazo",
    "preço a prazo": "preco_prazo",
    "apra": "preco_prazo",
    "a prazo": "preco_prazo",

}

class MapeamentoCampos:
    def __init__(self, df):
        self.df = df

    def normalizar(self, col):
        import unicodedata
        x = str(col).strip().lower()
        x = unicodedata.normalize('NFKD', x)
        x = ''.join(c for c in x if not unicodedata.combining(c))
        x = re.sub(r'[^a-z0-9 ]', '', x)
        return x

    def map_coluna(self, col):
        norm = self.normalizar(col)
        return BASE_ALIAS.get(norm, norm)

    def mapear(self):
        novas = []
        for col in self.df.columns:
            novas.append(self.map_coluna(col))
        self.df.columns = novas
        return self.df
