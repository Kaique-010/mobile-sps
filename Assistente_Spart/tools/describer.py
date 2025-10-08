from langchain_core.tools import BaseTool

def gerar_descricao_tools(tools, markdown=False):
    """
    Gera um texto descritivo das ferramentas disponíveis.
    Não executa as tools — apenas coleta nome e descrição.
    """
    linhas = []
    for t in tools:
        if isinstance(t, BaseTool):
            nome = getattr(t, "name", t.__class__.__name__)
            desc = getattr(t, "description", "").strip()
            if markdown:
                linhas.append(f"### 🧩 `{nome}`\n{desc}\n")
            else:
                linhas.append(f"- {nome}: {desc}")
        else:
            # caso alguma tool não seja BaseTool (ex: função decorada)
            nome = getattr(t, "__name__", str(t))
            desc = getattr(t, "__doc__", "").strip() or "Sem descrição disponível."
            if markdown:
                linhas.append(f"### 🧩 `{nome}`\n{desc}\n")
            else:
                linhas.append(f"- {nome}: {desc}")

    if markdown:
        return "## 🧠 Ferramentas disponíveis:\n\n" + "\n".join(linhas)
    else:
        return "Ferramentas disponíveis:\n" + "\n".join(linhas)
