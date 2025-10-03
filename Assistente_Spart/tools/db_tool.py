from langchain_core.tools import tool
from Produtos.models import Produtos, SaldoProduto, UnidadeMedida
from core.utils import get_db_from_slug
from core.middleware import get_licenca_slug

@tool
def procura_db(query: str) -> str:
    """
    Procura o banco de dados para responder à pergunta do usuário.
    útil para recuperar informações armazenadas no banco de dados.
    """
    # Lógica para procurar no banco de dados
    return f"Resultado da busca no banco de dados para: {query}"


@tool
def cadastrar_produtos(prod_nome: str, prod_ncm: str, banco: str = "default", empresa_id: str = "1", filial_id: str = "1") -> str:
    """
    Cadastra produtos no banco de dados respeitando empresa/filial do usuário logado.
    """
    # Resolver alias do banco a partir do slug do middleware quando vier "default" ou vazio
    real_banco = get_db_from_slug(get_licenca_slug()) if not banco or banco == "default" else banco
    # Verificar se a unidade de medida "UN" existe, senão criar
    unidade_medida, created = UnidadeMedida.objects.using(real_banco).get_or_create(
        unid_codi="UN",
        defaults={"unid_desc": "Unidade"}
    )

    ultimo_codigo = Produtos.objects.using(real_banco).filter(
        prod_empr=empresa_id
    ).order_by('-prod_codi').first()

    proximo_codigo = int(ultimo_codigo.prod_codi) + 1 if ultimo_codigo and str(ultimo_codigo.prod_codi).isdigit() else 1

    while Produtos.objects.using(real_banco).filter(prod_codi=str(proximo_codigo), prod_empr=empresa_id).exists():
        proximo_codigo += 1

    novo_produto = Produtos.objects.using(real_banco).create(
        prod_empr=empresa_id,
        prod_codi=str(proximo_codigo),
        prod_nome=prod_nome,
        prod_ncm=prod_ncm,
        prod_unme=unidade_medida,
        prod_orig_merc="0",
        prod_codi_nume=str(proximo_codigo)
    )

    return f"Produto {novo_produto.prod_nome} cadastrado na empresa {empresa_id}, filial {filial_id}, com código: {novo_produto.prod_codi}"


@tool
def consultar_saldo(produto_codigo: str, banco: str = "default", empresa_id: str = "1", filial_id: str = "1") -> str:
    """
    Consulta saldo do produto de acordo com empresa/filial do usuário logado.
    """
    # Resolver alias do banco a partir do slug do middleware quando vier "default" ou vazio
    real_banco = get_db_from_slug(get_licenca_slug()) if not banco or banco == "default" else banco
    try:
        produto = Produtos.objects.using(real_banco).get(prod_codi=produto_codigo, prod_empr=empresa_id)
    except Produtos.DoesNotExist:
        return f"Produto com código {produto_codigo} não encontrado para empresa {empresa_id}."

    saldo = SaldoProduto.objects.using(real_banco).filter(
        produto_codigo=produto,
        empresa=empresa_id,
        filial=filial_id
    ).first()

    if not saldo:
        return f"Nenhum saldo encontrado para o produto {produto.prod_nome} na empresa {empresa_id}, filial {filial_id}."

    return f"Saldo do produto {produto.prod_nome} (código {produto_codigo}) na empresa {empresa_id}, filial {filial_id}: {saldo.saldo_estoque}"
