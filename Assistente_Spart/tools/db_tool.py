from langchain_core.tools import tool
from Produtos.models import Produtos, SaldoProduto, UnidadeMedida
from core.utils import get_db_from_slug
from core.middleware import get_licenca_slug

from langchain_openai import ChatOpenAI
from django.db import connection
from django.db import connections
from ..configuracoes.config import CHAT_MODEL
from datetime import datetime, timedelta
from statistics import mean
from collections import Counter
import json
import re

llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)

_Schema_Cache = {}
_TTL = timedelta(minutes=120)


def ler_schema_db(slug: str = "default") -> dict:
    agora = datetime.now()
    cache = _Schema_Cache.get(slug)
    if cache and agora < cache["expira"]:
        return cache["schema"]

    conexao = connections[slug]
    schema = {}
    with conexao.cursor() as cursor:
        cursor.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """)
        for tabela, coluna, tipo in cursor.fetchall():
            schema.setdefault(tabela, []).append({'coluna': coluna, 'tipo': tipo})

    _Schema_Cache[slug] = {'schema': schema, 'expira': agora + _TTL}
    return schema
 
       

def relacionamentos_heuristicos(schema: dict) -> list:
    """
    Analisa o esquema do banco de dados e identifica relacionamentos heurísticos.
    Baseia-se em nomes de colunas similares entre tabelas.
    """
    rels = []
    tabelas = list(schema.keys())

    for t1 in tabelas:
        for t2 in tabelas:
            if t1 == t2:
                continue

            colunas1 = [c['coluna'] for c in schema[t1]]
            colunas2 = [c['coluna'] for c in schema[t2]]

            # Heurística: nomes de colunas iguais ou com sufixos semelhantes
            for c1 in colunas1:
                for c2 in colunas2:
                    if c1 == c2 and len(c1) > 3:
                        rels.append((t1, c1, t2, c2))
                    elif re.sub(r"_id$", "", c1) == re.sub(r"_id$", "", c2):
                        rels.append((t1, c1, t2, c2))

    # Remove duplicados
    rels_unicos = list({(a, b, c, d) for a, b, c, d in rels})
    return rels_unicos

def gerar_sql(pergunta: str, schema: dict, relacionamentos: list) -> str:
    """Gera SQL a partir de pergunta e contexto de schema e relacionamentos."""
    schema_txt = json.dumps(schema, ensure_ascii=False, indent=2)
    rel_txt = "\n".join([f"{a}.{b} ↔ {c}.{d}" for a, b, c, d in relacionamentos])

    prompt = f"""
Você é um gerador de SQL para PostgreSQL.
Regras:
- Gere apenas SELECTs válidos.
- Use as tabelas e colunas listadas.
- Utilize os relacionamentos sugeridos para JOINs.
- NÃO invente nomes.
- NÃO use funções de modificação (INSERT/UPDATE/DELETE).
- Retorne o SQL puro, sem explicações.

Schema:
{schema_txt}

Relacionamentos conhecidos:
{rel_txt}

Pergunta:
{pergunta}
"""
    resposta = llm.invoke(prompt)
    return resposta.content.strip()


def gerar_insights(colunas, linhas):
    """Gera insights descritivos e tendências com base nos dados retornados."""
    if not linhas:
        return "Nenhum dado encontrado."

    texto = []
    texto.append(f"Foram encontrados {len(linhas)} registros no total.")

    # Colunas numéricas
    numericas = []
    for i, col in enumerate(colunas):
        valores = [r[i] for r in linhas if isinstance(r[i], (int, float))]
        if valores:
            numericas.append((col, valores))

    # Estatísticas básicas
    for nome, valores in numericas:
        texto.append(
            f"A coluna '{nome}' possui média de {round(mean(valores), 2)}, "
            f"mínimo {min(valores)} e máximo {max(valores)}."
        )

        # Tendência simples (baseada na sequência temporal)
        if len(valores) >= 4:
            primeira_metade = mean(valores[: len(valores) // 2])
            segunda_metade = mean(valores[len(valores) // 2 :])
            if segunda_metade > primeira_metade * 1.05:
                texto.append(f"Houve tendência de crescimento em '{nome}' nos dados recentes.")
            elif segunda_metade < primeira_metade * 0.95:
                texto.append(f"'{nome}' apresentou leve queda ao longo do período.")

    # Coluna categórica principal (texto)
    col_text = next(
        (i for i, c in enumerate(colunas)
         if not all(isinstance(v, (int, float, type(None))) for v in [r[i] for r in linhas])),
        None
    )
    if col_text is not None:
        top = Counter([r[col_text] for r in linhas if r[col_text]]).most_common(3)
        if top:
            texto.append("Categorias mais recorrentes:")
            for val, freq in top:
                texto.append(f" - {val}: {freq} ocorrências")

    return "\n".join(texto)


@tool
def consulta_inteligente_prime(pergunta: str, slug: str = "default") -> str:
    """
    Executa uma consulta inteligente no banco PostgreSQL.
    Analisa o schema (com cache), infere relacionamentos e retorna somente os insights finais.
    """
    try:
        schema = ler_schema_db(slug)
        rels = relacionamentos_heuristicos(schema)
        sql = gerar_sql(pergunta, schema, rels)

        if not isinstance(sql, str) or not sql.strip().lower().startswith("select"):
            return "A consulta gerada não é um SELECT válido. Reformule a pergunta."

        conn = connections[slug]
        with conn.cursor() as cur:
            cur.execute(sql)
            colunas = [desc[0] for desc in cur.description]
            linhas = cur.fetchall()

        insights = gerar_insights(colunas, linhas)
        resposta = f"📊 Resultado da análise baseada na pergunta:\n\n{insights}"
        return str(resposta)
    except Exception as e:
        return f"Erro ao executar consulta: {e}"

@tool
def cadastrar_produtos(prod_nome: str, prod_ncm: str, banco: str = "default", empresa_id: str = "1", filial_id: str = "1") -> str:
    """
    Cadastra produto no banco atual (slug) respeitando empresa/filial.
    """
    try:
        real_banco = get_db_from_slug(get_licenca_slug()) if not banco or banco == "default" else banco
        unidade_medida, _ = UnidadeMedida.objects.using(real_banco).get_or_create(
            unid_codi="UN",
            defaults={"unid_desc": "Unidade"}
        )

        ultimo_codigo = Produtos.objects.using(real_banco).filter(
            prod_empr=empresa_id
        ).order_by('-prod_codi').first()

        proximo_codigo = int(ultimo_codigo.prod_codi) + 1 if ultimo_codigo and str(ultimo_codigo.prod_codi).isdigit() else 1
        while Produtos.objects.using(real_banco).filter(prod_codi=str(proximo_codigo), prod_empr=empresa_id).exists():
            proximo_codigo += 1

        novo = Produtos.objects.using(real_banco).create(
            prod_empr=empresa_id,
            prod_codi=str(proximo_codigo),
            prod_nome=prod_nome,
            prod_ncm=prod_ncm,
            prod_unme=unidade_medida,
            prod_orig_merc="0",
            prod_codi_nume=str(proximo_codigo)
        )
        return f"✅ {novo.prod_nome} criado (cód {novo.prod_codi}) na emp {empresa_id}/fil {filial_id}."
    except Exception as e:
        return f"❌ Erro ao cadastrar produto: {e}"


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
