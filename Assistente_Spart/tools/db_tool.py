from langchain_core.tools import tool
from Entidades.models import Entidades
from Produtos.models import Produtos, SaldoProduto, UnidadeMedida
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from Pedidos.models import PedidosGeral, PedidoVenda, Itenspedidovenda
from Pedidos.services.pedido_service import PedidoVendaService
from core.utils import get_db_from_slug
from core.middleware import get_licenca_slug
from django.db.models import Count, Sum, Q
import traceback
from langchain_openai import ChatOpenAI
from django.db import connections, connection
from ..configuracoes.config import CHAT_MODEL
from datetime import datetime, timedelta
from statistics import mean
from collections import Counter
import json
import re

import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)

_Schema_Cache = {}
_TTL = timedelta(minutes=120)


def normalizar_itens_pedido(itens_data: list) -> list:
    itens_normalizados = []

    for idx, item in enumerate(itens_data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx} inválido: esperado objeto.")

        produto = (
            item.get("iped_prod")
            or item.get("produto_codigo")
            or item.get("produto")
            or item.get("codigo_produto")
        )

        quantidade = (
            item.get("iped_quan")
            or item.get("quantidade")
            or item.get("qtd")
        )

        valor_unitario = (
            item.get("iped_unit")
            or item.get("valor_unitario")
            or item.get("preco_unitario")
            or item.get("preco")
            or item.get("valor")
        )

        desconto = (
            item.get("iped_desc")
            or item.get("desconto")
            or "0"
        )

        lote = item.get("iped_lote_vend") or item.get("lote")

        if not produto:
            raise ValueError(f"Item {idx}: produto não informado.")
        if quantidade in (None, "", 0, "0"):
            raise ValueError(f"Item {idx}: quantidade não informada ou inválida.")
        if valor_unitario in (None, "", 0, "0"):
            raise ValueError(f"Item {idx}: valor unitário não informado ou inválido.")

        item_final = {
            "iped_prod": str(produto),
            "iped_quan": str(quantidade),
            "iped_unit": str(valor_unitario),
            "iped_desc": str(desconto),
        }

        if lote not in (None, ""):
            item_final["iped_lote_vend"] = lote

        itens_normalizados.append(item_final)

    return itens_normalizados


def _normalizar_data_filtro(data_valor: str, is_fim: bool = False) -> str:
    if not data_valor:
        return data_valor
    texto = str(data_valor).strip()
    if not texto:
        return texto
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except Exception:
            continue
    meses = {
        'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9,
        'outubro': 10, 'novembro': 11, 'dezembro': 12,
    }
    m = re.match(r"(?i)^([a-zçãõáéíóú]+)\s+de\s+(\d{4})$", texto)
    if m:
        from calendar import monthrange
        mes = meses.get(m.group(1).strip().lower())
        ano = int(m.group(2))
        if mes:
            dia = monthrange(ano, mes)[1] if is_fim else 1
            return f"{ano:04d}-{mes:02d}-{dia:02d}"
    return texto

def _extrair_select(sql_texto: str) -> str:
    if not sql_texto:
        return ""
    t = str(sql_texto).strip()
    m = re.search(r"```(?:sql)?\s*([\s\S]*?)```", t, flags=re.IGNORECASE)
    if m:
        t = m.group(1).strip()
    t = re.sub(r"^(sql\s*:)", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^(query\s*:)", "", t, flags=re.IGNORECASE).strip()
    m = re.search(r"\bselect\b[\s\S]*", t, flags=re.IGNORECASE)
    if m:
        t = m.group(0).strip()
    t = t.strip().rstrip(";").strip()
    return t


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
    OTIMIZADO: Usa dicionário reverso e ignora colunas genéricas.
    """
    # Colunas genéricas que não devem gerar relacionamentos automáticos
    IGNORED_COLS = {
        'id', 'uuid', 'created_at', 'updated_at', 'deleted_at', 
        'status', 'ativo', 'obs', 'observacao', 'nome', 'descricao',
        'data_cadastro', 'data_alteracao'
    }
    
    # Mapa: nome_normalizado -> lista de (tabela, coluna_original)
    col_map = defaultdict(list)
    
    tabelas = list(schema.keys())
    for t in tabelas:
        for col_info in schema[t]:
            c = col_info['coluna']
            
            if c.lower() in IGNORED_COLS:
                continue
                
            # Normaliza removendo sufixo _id
            norm = re.sub(r"_id$", "", c.lower())
            
            # Ignora termos muito curtos após normalização
            if len(norm) < 3:
                continue
                
            col_map[norm].append((t, c))
            
    rels = set()
    
    for norm, ocorrencias in col_map.items():
        if len(ocorrencias) < 2:
            continue
            
        # Gera pares entre tabelas diferentes
        for i in range(len(ocorrencias)):
            for j in range(i + 1, len(ocorrencias)):
                t1, c1 = ocorrencias[i]
                t2, c2 = ocorrencias[j]
                
                if t1 == t2:
                    continue
                
                # Garante ordem alfabética para consistência (A <-> B)
                if t1 < t2:
                    rels.add((t1, c1, t2, c2))
                else:
                    rels.add((t2, c2, t1, c1))

    return list(rels)

def gerar_sql(pergunta: str, schema: dict, relacionamentos: list) -> str:
    """Gera SQL a partir de pergunta e contexto de schema e relacionamentos."""
    # Reduz o schema apenas para tabelas relevantes (Heurística simples baseada em keywords)
    # Se o schema for muito grande, o LLM estoura o limite de tokens.
    
    tabelas_filtradas = {}
    keywords = set(re.findall(r"\w{4,}", pergunta.lower()))
    
    # 1. Tenta encontrar tabelas que contenham keywords da pergunta
    for tabela, cols in schema.items():
        if any(k in tabela.lower() for k in keywords):
            tabelas_filtradas[tabela] = cols
            continue
        # 2. Ou que tenham colunas com keywords
        for col in cols:
            if any(k in col['coluna'].lower() for k in keywords):
                tabelas_filtradas[tabela] = cols
                break
    
    # Se não encontrou nada ou se a pergunta for muito genérica, usa todo o schema (com risco)
    # Mas se o schema original for gigante (>50 tabelas), pega só as top 20 mais "conectadas" ou apenas as filtradas
    if not tabelas_filtradas and len(schema) < 50:
        tabelas_filtradas = schema
    elif not tabelas_filtradas:
        # Fallback: pega as primeiras 20 tabelas (melhor que estourar erro)
        tabelas_filtradas = dict(list(schema.items())[:20])
        
    schema_txt = json.dumps(tabelas_filtradas, ensure_ascii=False, indent=2)
    
    # Filtra relacionamentos apenas das tabelas selecionadas
    rels_filtrados = [
        r for r in relacionamentos 
        if r[0] in tabelas_filtradas and r[2] in tabelas_filtradas
    ]
    rel_txt = "\n".join([f"{a}.{b} ↔ {c}.{d}" for a, b, c, d in rels_filtrados])
    
    # PROTEÇÃO CONTRA ESTOURO DE CONTEXTO (HARD LIMIT)
    # gpt-4o tem limite de 128k tokens, mas o output é limitado. 
    # Manter input < 100k chars é seguro.
    if len(schema_txt) + len(rel_txt) > 100000:
        logger.warning(f"⚠️ Contexto muito grande ({len(schema_txt) + len(rel_txt)} chars). Truncando schema...")
        # Pega apenas as primeiras 5 tabelas se estourar
        tabelas_filtradas = dict(list(tabelas_filtradas.items())[:5])
        schema_txt = json.dumps(tabelas_filtradas, ensure_ascii=False, indent=2)
        
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
    try:
        resposta = llm.invoke(prompt)
        return _extrair_select(getattr(resposta, "content", ""))
    except Exception as e:
        logger.error(f"❌ Erro ao invocar LLM para gerar SQL: {e}")
        return "" # Retorna vazio para ser tratado pelo chamador


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
    inicio = time.time()
    
    try:
        # Validação de entrada
        if not pergunta or not pergunta.strip():
            return "❌ Pergunta não pode estar vazia."
        
        if not slug:
            slug = "default"
            
        # Verificar se a conexão existe
        if slug not in connections:
            return f"❌ Banco de dados '{slug}' não encontrado."
        
        schema = ler_schema_db(slug)
        
        if not schema:
            return "❌ Não foi possível obter o schema do banco de dados."
            
        rels = relacionamentos_heuristicos(schema)

        sql = gerar_sql(pergunta, schema, rels)

        if not isinstance(sql, str) or not sql.strip():
            return "❌ Não foi possível gerar uma consulta SQL válida."
            
        if not sql.strip().lower().startswith("select"):
            return "❌ A consulta gerada não é um SELECT válido. Reformule a pergunta."

        conn = connections[slug]
        with conn.cursor() as cur:
            try:
                cur.execute(sql)
                colunas = [desc[0] for desc in cur.description] if cur.description else []
                
                # Proteção contra OOM/Hang: Limita a 5000 linhas
                linhas = cur.fetchmany(5000)
                if len(linhas) >= 5000:
                    logger.warning(f"⚠️ Resultado truncado em 5000 linhas (SQL: {sql[:100]}...)")
                    
            except Exception as db_error:
                return f"❌ Erro ao executar consulta SQL: {str(db_error)}"

        # Verifica se há resultados
        if not linhas:
            return "ℹ️ Consulta executada com sucesso, mas não retornou resultados."

        insights = gerar_insights(colunas, linhas)
        if not insights or insights.strip() == "":
            # Fallback: retorna dados brutos formatados
            resultado_formatado = f"Resultados para: {pergunta}\n\n"
            for i, linha in enumerate(linhas[:10]):  # Limita a 10 linhas
                resultado_formatado += f"Linha {i+1}: {dict(zip(colunas, linha))}\n"
            if len(linhas) > 10:
                resultado_formatado += f"... e mais {len(linhas) - 10} registros"
            return resultado_formatado
        
        resposta = f"📊 Resultado da análise baseada na pergunta:\n\n{insights}"
        return str(resposta)
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Erro interno ao executar consulta: {str(e)}"
        try:
            logger.error(f"[CONSULTA_INTELIGENTE] {error_msg}\n{traceback.format_exc()}")
        except:
            pass
        return error_msg

@tool
def cadastrar_produtos(prod_nome: str, prod_ncm: str, banco: str = "default",
                       empresa_id: str = "1", filial_id: str = "1") -> str:
    """Cadastra produto no banco correto."""
    try:
        # Banco real vem direto do agente ou da view
        real_banco = banco or "default"
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
        return f"✅ {novo.prod_nome} criado (cód {novo.prod_codi}) no banco {real_banco} (emp {empresa_id}/fil {filial_id})."
    except Exception as e:
        return f"❌ Erro ao cadastrar produto no banco {real_banco} (emp {empresa_id}/fil {filial_id}): {e}"


@tool
def consultar_saldo(produto_codigo: str, banco: str = "default",
                    empresa_id: str = "1", filial_id: str = "1") -> str:
    """Consulta saldo respeitando o banco recebido."""
    try:
        real_banco = banco or "default"
        produto = Produtos.objects.using(real_banco).get(prod_codi=produto_codigo, prod_empr=empresa_id)
    except Produtos.DoesNotExist:
        return f"Produto {produto_codigo} não encontrado na empresa {empresa_id} (banco {real_banco})."

    saldo = SaldoProduto.objects.using(real_banco).filter(
        produto_codigo=produto,
        empresa=empresa_id,
        filial=filial_id
    ).first()

    if not saldo:
        return f"Nenhum saldo encontrado no banco {real_banco} para {produto.prod_nome} (emp {empresa_id}, fil {filial_id})."

    return f"Saldo de {produto.prod_nome} (cód {produto_codigo}) no banco {real_banco}: {saldo.saldo_estoque}"


@tool
def consultar_titulos_a_pagar(banco: str = "default",
                    empresa_id: str = "1", filial_id: str = "1") -> str:
    """Consulta títulos a pagar respeitando o banco recebido."""
    
    try:
        real_banco = banco or "default"
        
        # Validação de entrada
        if not empresa_id or not filial_id:
            return "❌ Empresa e filial são obrigatórios."
        
        titulos = Titulospagar.objects.using(real_banco).filter(
            titu_empr=empresa_id,
            titu_fili=filial_id,
            titu_aber__in=['A', 'P']
        )
        
        if not titulos.exists():
            return f"ℹ️ Nenhum título a pagar encontrado na empresa {empresa_id}, filial {filial_id}."
        
        resultado = f"📋 Títulos a pagar - Empresa {empresa_id}, Filial {filial_id}:\n\n"
        total_valor = 0
        
        for titulo in titulos[:100]:  # Limita a 100 registros
            try:
                valor = float(getattr(titulo, 'titu_valo', 0) or 0)
                vencimento = getattr(titulo, 'titu_venc', 'N/A')
                from Entidades.models import Entidades
                fornecedor_nome = Entidades.objects.using(real_banco).get(enti_clie=titulo.titu_forn).enti_nome or getattr(titulo, 'titu_forn', 'N/A')
                
                resultado += f"• Fornecedor: {fornecedor_nome} | Valor: R$ {valor:,.2f} | Vencimento: {vencimento}\n"
                total_valor += valor
            except Exception as item_error:
                continue  # Ignora itens com erro
        
        if titulos.count() > 100:
            resultado += f"\n... e mais {titulos.count() - 100} títulos\n"
        
        resultado += f"\n💰 Total geral: R$ {total_valor:,.2f}"
        return resultado
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Erro ao consultar títulos a pagar: {str(e)}"
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[TITULOS_PAGAR] {error_msg}\n{traceback.format_exc()}")
        except:
            pass
        return error_msg


@tool
def consultar_titulos_a_receber(banco: str = "default",
                    empresa_id: str = "1", filial_id: str = "1") -> str:
    """Consulta títulos a receber respeitando o banco recebido."""
    
    try:
        real_banco = banco or "default"
        
        # Validação de entrada
        if not empresa_id or not filial_id:
            return "❌ Empresa e filial são obrigatórios."
        
        titulos = Titulosreceber.objects.using(real_banco).filter(
            titu_empr=empresa_id,
            titu_fili=filial_id,
            titu_aber='A'
        )
        
        if not titulos.exists():
            return f"ℹ️ Nenhum título a receber encontrado na empresa {empresa_id}, filial {filial_id}."
        
        resultado = f"📋 Títulos a receber - Empresa {empresa_id}, Filial {filial_id}:\n\n"
        total_valor = 0
        
        for titulo in titulos[:100]:  # Limita a 100 registros
            try:
                valor = float(getattr(titulo, 'titu_valo', 0) or 0)
                vencimento = getattr(titulo, 'titu_venc', 'N/A')
                from Entidades.models import Entidades
                cliente_nome = Entidades.objects.using(real_banco).get(enti_clie=titulo.titu_clie).enti_nome or getattr(titulo, 'titu_clie', 'N/A')
                
                resultado += f"• Cliente: {cliente_nome} | Valor: R$ {valor:,.2f} | Vencimento: {vencimento}\n"
                total_valor += valor
            except Exception as item_error:
                continue  # Ignora itens com erro
        
        if titulos.count() > 100:
            resultado += f"\n... e mais {titulos.count() - 100} títulos\n"
        
        resultado += f"\n💰 Total geral: R$ {total_valor:,.2f}"
        return resultado
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Erro ao consultar títulos a receber: {str(e)}"
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[TITULOS_RECEBER] {error_msg}\n{traceback.format_exc()}")
        except:
            pass
        return error_msg

@tool
def historico_de_pedidos(banco: str = "default",
                    empresa_id: str = "1", filial_id: str = "1",
                    data_inicial: str = None, data_final: str = None) -> str:
    """Relatório de pedidos por cliente com filtro de data."""
    try:
        real_banco = banco or "default"
        if not empresa_id or not filial_id:
            return "❌ Empresa e filial são obrigatórios."
        qs = PedidosGeral.objects.using(real_banco).filter(
            empresa=empresa_id,
            filial=filial_id,
        )
        if data_inicial:
            qs = qs.filter(data_pedido__gte=data_inicial)
        if data_final:
            qs = qs.filter(data_pedido__lte=data_final)
        if not qs.exists():
            periodo = ""
            if data_inicial or data_final:
                periodo = f" no período {data_inicial or 'início'} a {data_final or 'hoje'}"
            return f"ℹ️ Nenhum pedido encontrado na empresa {empresa_id}, filial {filial_id}{periodo}."
        agregados = qs.values("codigo_cliente", "nome_cliente").annotate(
            total_pedidos=Count("numero_pedido"),
            valor_total=Sum("valor_total")
        ).order_by("nome_cliente")
        soma_valor = qs.aggregate(soma=Sum("valor_total"))
        total_pedidos = qs.count()
        total_clientes = agregados.count()
        titulo_periodo = ""
        if data_inicial or data_final:
            titulo_periodo = f" — Período {data_inicial or 'início'} a {data_final or 'hoje'}"
        resultado = f"📋 Relatório de pedidos por cliente — Empresa {empresa_id}, Filial {filial_id}{titulo_periodo}:\n\n"
        for item in agregados[:200]:
            nome = item["nome_cliente"] or str(item["codigo_cliente"]) or "N/A"
            valor = float(item["valor_total"] or 0)
            qtd = int(item["total_pedidos"] or 0)
            resultado += f"• Cliente: {nome} | Pedidos: {qtd} | Total: R$ {valor:,.2f}\n"
        if agregados.count() > 200:
            resultado += f"\n... e mais {agregados.count() - 200} clientes\n"
        valor_geral = float(soma_valor.get("soma") or 0)
        ticket_medio = valor_geral / total_pedidos if total_pedidos else 0
        top = sorted(agregados, key=lambda x: x["valor_total"] or 0, reverse=True)
        if top:
            lider_nome = top[0]["nome_cliente"] or str(top[0]["codigo_cliente"]) or "N/A"
            lider_valor = float(top[0]["valor_total"] or 0)
            participacao = (lider_valor / valor_geral * 100) if valor_geral else 0
            resultado += f"\n📈 Insight: Cliente líder {lider_nome} com R$ {lider_valor:,.2f} ({participacao:.1f}% do período)\n"
        resultado += f"\n🔢 Clientes: {total_clientes} | Pedidos: {total_pedidos} | Faturamento: R$ {valor_geral:,.2f} | Ticket médio: R$ {ticket_medio:,.2f}"
        return resultado
    except Exception as e:
        import traceback
        error_msg = f"❌ Erro ao consultar histórico de pedidos: {str(e)}"
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[HISTORICO_PEDIDOS] {error_msg}\n{traceback.format_exc()}")
        except:
            pass
        return error_msg

@tool
def historico_de_pedidos_cliente(banco: str = "default",
                    empresa_id: str = "1", filial_id: str = "1",
                    data_inicial: str = None, data_final: str = None,
                    codigo_cliente: str = None, nome_cliente: str = None) -> str:
    """Relatório de pedidos por cliente específico com filtro de data."""
    try:
        real_banco = banco or "default"
        if not empresa_id or not filial_id:
            return "❌ Empresa e filial são obrigatórios."
        qs = PedidosGeral.objects.using(real_banco).filter(
            empresa=empresa_id,
            filial=filial_id,
        )
        if data_inicial:
            qs = qs.filter(data_pedido__gte=data_inicial)
        if data_final:
            qs = qs.filter(data_pedido__lte=data_final)
        if codigo_cliente:
            qs = qs.filter(codigo_cliente=codigo_cliente)
        elif nome_cliente:
            qs = qs.filter(nome_cliente__icontains=nome_cliente)
        if not qs.exists():
            alvo = nome_cliente or codigo_cliente or "cliente informado"
            periodo = ""
            if data_inicial or data_final:
                periodo = f" no período {data_inicial or 'início'} a {data_final or 'hoje'}"
            return f"ℹ️ Nenhum pedido encontrado para {alvo} na empresa {empresa_id}, filial {filial_id}{periodo}."
        agg = qs.aggregate(
            total_pedidos=Count("numero_pedido"),
            valor_total=Sum("valor_total")
        )
        nome = qs.values_list("nome_cliente", flat=True).first() or str(qs.values_list("codigo_cliente", flat=True).first()) or "N/A"
        valor_geral = float(agg.get("valor_total") or 0)
        qtd = int(agg.get("total_pedidos") or 0)
        ticket_medio = valor_geral / qtd if qtd else 0
        titulo_periodo = ""
        if data_inicial or data_final:
            titulo_periodo = f" — Período {data_inicial or 'início'} a {data_final or 'hoje'}"
        resultado = f"📋 Relatório de pedidos do cliente — Empresa {empresa_id}, Filial {filial_id}{titulo_periodo}:\n\n"
        resultado += f"• Cliente: {nome} | Pedidos: {qtd} | Total: R$ {valor_geral:,.2f}\n"
        resultado += f"\n🔢 Ticket médio: R$ {ticket_medio:,.2f}"
        return resultado
    except Exception as e:
        import traceback
        error_msg = f"❌ Erro ao consultar histórico de pedidos do cliente: {str(e)}"
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[HISTORICO_PEDIDOS_CLIENTE] {error_msg}\n{traceback.format_exc()}")
        except:
            pass
        return error_msg

@tool
def total_pedidos_periodo(
    banco: str = "default",
    empresa_id: str = "1",
    filial_id: str = "1",
    data_inicial: str = None,
    data_final: str = None,
    status: str = None,
) -> str:
    """Retorna total e valor de pedidos por período, com filtro opcional de status."""
    try:
        real_banco = banco or "default"
        data_inicial = _normalizar_data_filtro(data_inicial, is_fim=False)
        data_final = _normalizar_data_filtro(data_final, is_fim=True)
        periodo_txt = ""
        if data_inicial or data_final:
            periodo_txt = f" — Período {data_inicial or 'início'} a {data_final or 'hoje'}"

        status_txt = f" | Status: {status}" if status else ""

        qs_g = PedidosGeral.objects.using(real_banco).filter(
            empresa=empresa_id,
            filial=filial_id,
        )
        if data_inicial:
            qs_g = qs_g.filter(data_pedido__gte=data_inicial)
        if data_final:
            qs_g = qs_g.filter(data_pedido__lte=data_final)

        total_view = qs_g.count()
        valor_view = qs_g.aggregate(soma=Sum("valor_total")).get("soma") or 0
        itens_view = qs_g.aggregate(soma=Sum("quantidade_total")).get("soma") or 0

        if not status:
            return (
                f"📌 Total de pedidos{periodo_txt} — Empresa {empresa_id}, Filial {filial_id}:\n\n"
                f"• Quantidade: {total_view}\n"
                f"• Valor total: R$ {float(valor_view or 0):,.2f}\n"
                f"• Itens: {float(itens_view or 0):,.2f}"
            )

        st = str(status).strip().lower()
        status_map = {
            "pendente": "Pendente",
            "aberto": "Pendente",
            "processando": "Processando",
            "enviado": "Enviado",
            "concluido": "Concluído",
            "concluído": "Concluído",
            "confirmado": "Concluído",
            "confirmados": "Concluído",
            "cancelado": "Cancelado",
            "cancelados": "Cancelado",
        }
        status_resolvido = status_map.get(st)
        if status_resolvido is None:
            status_raw = str(status).strip()
            status_por_codigo = {
                "0": "Pendente",
                "1": "Processando",
                "2": "Enviado",
                "3": "Concluído",
                "4": "Cancelado",
            }
            status_resolvido = status_por_codigo.get(status_raw, status_raw)

        qs_status = qs_g.filter(status__iexact=status_resolvido)
        total = qs_status.count()
        valor_total = qs_status.aggregate(soma=Sum("valor_total")).get("soma") or 0
        itens_status = qs_status.aggregate(soma=Sum("quantidade_total")).get("soma") or 0
        status_txt = f" | Status: {status_resolvido}"

        resposta = (
            f"📌 Total de pedidos{periodo_txt} — Empresa {empresa_id}, Filial {filial_id}{status_txt}:\n\n"
            f"• Quantidade: {total}\n"
            f"• Valor total: R$ {float(valor_total or 0):,.2f}\n"
            f"• Itens: {float(itens_status or 0):,.2f}"
        )

        if total_view and total != total_view:
            resposta += (
                f"\n\nℹ️ Total geral no período em pedidos_geral: {total_view} pedidos"
                f"\nℹ️ Itens no período em pedidos_geral: {float(itens_view or 0):,.2f}"
            )

        return resposta
    except Exception as e:
        error_msg = f"❌ Erro ao consultar total de pedidos: {str(e)}"
        try:
            logger.error(f"[TOTAL_PEDIDOS_PERIODO] {error_msg}\n{traceback.format_exc()}")
        except Exception:
            pass
        return error_msg


@tool
def criar_pedido_de_venda(
    banco: str = "default",
    empresa_id: str = "1",
    filial_id: str = "1",
    cliente_id: str = "1",
    data_pedido: str = None,
    vendedor_id: str = None,
    itens: str = "[]",
    tipo_oper: str = "Venda",
    observacao: str = "Pedido de venda criado pelo Assistente Khronus",
) -> str:
    """Cria um pedido de venda no banco de dados com status 0"""
    try:
        real_banco = banco or "default"
        
        from datetime import datetime
        if not data_pedido:
            data_pedido = datetime.now().strftime("%Y-%m-%d")
        try:
            desconto_total = "0"
            itens_data = json.loads(itens) if itens else []
        except json.JSONDecodeError:
            itens_data = None
        except Exception:
            itens_data = None

        if not isinstance(itens_data, list) or not itens_data:
            return "❌ Erro: informe ao menos 1 item no pedido."
        try:
            itens_data = normalizar_itens_pedido(itens_data)
        except ValueError as e:
            return f"❌ Erro nos itens: {e}"
        pedido_dados = {
            "pedi_empr": int(empresa_id),
            "pedi_fili": int(filial_id),
            "pedi_forn": str(cliente_id),  
            "pedi_vend": int(vendedor_id) if vendedor_id not in (None, "", "null") else None,
            "pedi_data": data_pedido,
            "pedi_desc": desconto_total or "0",
            "pedi_obse": observacao or "",
            "pedi_stat": 0,
        }
        
        pedido = PedidoVendaService.create_pedido_venda(
            banco=real_banco,
            pedido_data=pedido_dados,
            itens_data=itens_data,
            pedi_tipo_oper=tipo_oper,
            request=None,
        )
        return (
            f"✅ Pedido criado com sucesso.\n"
            f"Pedido: {pedido.pedi_nume}\n"
            f"Cliente: {pedido.pedi_forn}\n"
            f"Total: {pedido.pedi_tota}\n"
            f"Empresa: {pedido.pedi_empr} | Filial: {pedido.pedi_fili}"
        )

    except Exception as e:
        error_msg = f"❌ Erro ao criar pedido de venda: {str(e)}"
        logger.error("[CRIAR_PEDIDO_DE_VENDA] %s\n%s", error_msg, traceback.format_exc())
        return error_msg