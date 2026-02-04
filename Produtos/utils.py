import hashlib
from django.conf import settings

def gerar_hash_etiqueta(produto):
    """Gera um hash único para o produto para uso na URL do QR Code"""
    raw = f"{produto.prod_empr}:{produto.prod_codi}:{settings.SECRET_KEY}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]

def formatar_dados_etiqueta(produto):
    """
    Formata os dados do produto para impressão de etiqueta.
    Retorna um dicionário com os campos necessários.
    """
    hash_etiqueta = gerar_hash_etiqueta(produto)
    
    # Determina o código de barras (prioridade: prod_coba > prod_gtin > prod_codi)
    barcode = produto.prod_coba or produto.prod_gtin or produto.prod_codi
    if barcode == 'SEM GTIN':
        barcode = produto.prod_codi

    # Obtém nome do fabricante (Marca)
    fabricante = "padrão"
    if produto.prod_marc:
        fabricante = produto.prod_marc.nome
    
    return {
        "codigo": produto.prod_codi,
        "descricao": produto.prod_nome,
        "fabricante": fabricante,
        "sku_fabrica": produto.prod_codi,
        "barcode": barcode,
        "qr_code_url": f"https://mobile-sps.site/p/{hash_etiqueta}",
        "hash_id": hash_etiqueta
    }
