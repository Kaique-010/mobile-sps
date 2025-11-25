from langchain_core.tools import tool



@tool
def fiscal_router(pergunta: str) -> str:
    """
    Analisa a pergunta do usuário e conduz o fluxo fiscal de forma natural.
    A própria ferramenta decide o subfluxo adequado (CFOP, impostos, emissão, etc.).

    A tool NÃO dá menu. Ela devolve uma contra-pergunta natural e contextual.
    """

    fluxo = identificar_fluxo(pergunta)

    # Emissão
    if fluxo == "emissao":
        base = emissao.handle(pergunta)
        return (
            "Parece que você está falando sobre emissão de NF-e/NFC-e.\n"
            "Antes de avançar, preciso entender em qual parte o problema ocorre.\n\n"
            f"{base}\n"
            "Me diga qual ponto exatamente está com dificuldade."
        )

    # Erros
    elif fluxo == "erros":
        base = erros.handle(pergunta)
        return (
            "Entendi que você está lidando com um erro em uma nota.\n"
            "Para identificar corretamente, me envie o *código do erro* ou um print.\n\n"
            f"{base}"
        )

    # CFOP
    elif fluxo == "cfop":
        base = cfop.handle(pergunta)
        return (
            "Ok, estamos falando de CFOP.\n"
            "Preciso só entender o tipo de operação para indicar o CFOP correto.\n\n"
            f"{base}"
        )

    # Impostos
    elif fluxo == "impostos":
        base = impostos.handle(pergunta)
        return (
            "Beleza, é dúvida sobre impostos da nota.\n"
            "Vou precisar de mais contexto sobre o tipo da operação e o regime.\n\n"
            f"{base}"
        )

    # Devolução
    elif fluxo == "devolucao":
        base = devolucao.handle(pergunta)
        return (
            "Você está falando de devolução.\n"
            "Para te orientar corretamente, preciso entender o tipo da devolução.\n\n"
            f"{base}"
        )

    # Cadastro
    elif fluxo == "cadastro":
        base = cadastro.handle(pergunta)
        return (
            "Certo, isso parece relacionado a cadastro de emitente, cliente ou produto.\n"
            "Me diga qual item você quer ajustar.\n\n"
            f"{base}"
        )

    # Não identificou → a LLM que decida
    return (
        "Isso parece relacionado à parte fiscal, mas preciso de mais detalhes.\n"
        "Você pode me explicar um pouco mais qual é a dificuldade?"
    )
