from langchain_core.tools import tool
import re
from .db_tool import cadastrar_produtos, consultar_saldo
from core.utils import get_db_from_slug

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


@tool
def executar_intencao(mensagem: str, banco: str = "default", slug: str = None, empresa_id: str = "1", filial_id: str = "1") -> str:
    """
    Executa a intenção detectada diretamente:
    - Cadastro: "produto <nome> ncm <codigo>"
    - Saldo: contém "saldo|estoque|quantidade" e "codigo|produto <número>"

    Retorna mensagem curta de sucesso/erro da tool chamada.
    """
    try:
        # Cadastro de produto
        m_cad = re.search(r"(?i)produto\s+(.+?)\s+ncm\s+(\d+)", mensagem)
        if m_cad:
            nome = m_cad.group(1).strip()
            ncm = m_cad.group(2).strip()
            # Resolver banco: se vier 'default' use slug corrente via utils
            real_banco = get_db_from_slug(slug) if (not banco or banco == "default") else banco
            # Chamar a função interna da tool para aceitar kwargs corretamente
            return cadastrar_produtos.func(
                prod_nome=nome,
                prod_ncm=ncm,
                banco=real_banco,
                empresa_id=str(empresa_id),
                filial_id=str(filial_id),
            )

        # Consulta de saldo
        m_saldo_kw = re.search(r"(?i)(saldo|estoque|quantidade)", mensagem)
        m_saldo_cod = re.search(r"(?i)(c[oó]digo|produto)\s+(\d+)", mensagem)
        if m_saldo_kw and m_saldo_cod:
            codigo = m_saldo_cod.group(2).strip()
            # Resolver banco: se vier 'default' use slug corrente via utils
            real_banco = get_db_from_slug(slug) if (not banco or banco == "default") else banco
            # Chamar a função interna da tool para aceitar kwargs corretamente
            return consultar_saldo.func(
                produto_codigo=codigo,
                banco=real_banco,
                empresa_id=str(empresa_id),
                filial_id=str(filial_id),
            )

        return "Não foi possível identificar a intenção com clareza."
    except Exception as e:
        return f"❌ Erro ao executar intenção: {e}"
