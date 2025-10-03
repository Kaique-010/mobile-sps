from langchain_core.tools import tool
import re

@tool
def identificar_intencao(mensagem: str) -> dict:
    """
    Identifica a intenção do Usuário (cadastrar produto ou consultar saldo).
    Extrai parâmetros relevantes da frase: nome, código, empresa, filial.
    """
    msg_lower = mensagem.lower()

    # Defaults
    empresa = "1"
    filial = "1"

    # Captura empresa
    empresa_match = re.search(r"empresa\s+(\d+)", msg_lower)
    if empresa_match:
        empresa = empresa_match.group(1)

    # Captura filial
    filial_match = re.search(r"filial\s+(\d+)", msg_lower)
    if filial_match:
        filial = filial_match.group(1)

    # Cadastro
    if "cadastro" in msg_lower or "cadastrar" in msg_lower or "novo produto" in msg_lower:
        nome = re.search(r"produto\s+(.+?)(?=\s+código|\s+preço|$)", msg_lower)
        codigo = re.search(r"código\s+(\d+)", msg_lower)

        return {
            "acao": "cadastrar_produto",
            "nome": nome.group(1).strip() if nome else None,
            "codigo": codigo.group(1) if codigo else None,
            "empresa": empresa,
            "filial": filial
        }

    # Consulta de saldo
    elif "saldo" in msg_lower or "quantidade" in msg_lower or "estoque" in msg_lower:
        codigo_match = re.search(r"produto\s+(\d+)", msg_lower)
        return {
            "acao": "consultar_saldo",
            "codigo": codigo_match.group(1) if codigo_match else None,
            "empresa": empresa,
            "filial": filial
        }

    return {"acao": "desconhecida", "empresa": empresa, "filial": filial}
