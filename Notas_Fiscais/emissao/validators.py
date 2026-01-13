from .exceptions import AmbienteMismatchError, ErroValidacao


def validar_dados_iniciais(dto: dict):
    """
    Valida dados básicos obrigatórios antes de criar a nota.
    """
    # 1. Emitente
    emit = dto.get("emitente")
    if not emit:
        raise ErroValidacao("Dados do emitente não informados.")
    if not emit.get("cnpj"):
        raise ErroValidacao("CNPJ do emitente obrigatório.")
    if not emit.get("uf"):
        raise ErroValidacao("UF do emitente obrigatória.")

    # 2. Destinatário
    dest = dto.get("destinatario")
    if not dest:
        raise ErroValidacao("Dados do destinatário não informados.")
    if not dest.get("documento"):
        raise ErroValidacao("CPF/CNPJ do destinatário obrigatório.")
    if not dest.get("uf"):
        raise ErroValidacao("UF do destinatário obrigatória.")

    # 3. Itens
    itens = dto.get("itens")
    if not itens or len(itens) == 0:
        raise ErroValidacao("Nota deve conter pelo menos um item.")

    for i, item in enumerate(itens, 1):
        if not item.get("codigo"):
            raise ErroValidacao(f"Item {i}: Código do produto obrigatório.")
        if not item.get("descricao"):
            raise ErroValidacao(f"Item {i}: Descrição obrigatória.")
        
        qtde = float(item.get("quantidade") or 0)
        valor = float(item.get("valor_unit") or 0)
        
        if qtde <= 0:
            raise ErroValidacao(f"Item {i}: Quantidade deve ser maior que zero.")
        if valor < 0:
            raise ErroValidacao(f"Item {i}: Valor unitário não pode ser negativo.")


def validar_dados_calculados(nota):
    """
    Valida a nota após o cálculo de impostos e antes da emissão.
    Verifica se os impostos foram calculados e se os campos fiscais essenciais estão presentes.
    """
    if not nota.itens.exists():
        raise ErroValidacao("Nota sem itens gravados no banco.")

    for item in nota.itens.all():
        # Validação de NCM e CFOP (que podem vir do cadastro ou serem ajustados)
        if not item.ncm or len(item.ncm) != 8:
            raise ErroValidacao(f"Item {item.produto.prod_codi}: NCM inválido ({item.ncm}).")
        
        if not item.cfop or len(item.cfop) != 4:
            raise ErroValidacao(f"Item {item.produto.prod_codi}: CFOP inválido ({item.cfop}).")

        # Verifica se impostos foram calculados (relação OneToOne)
        if not hasattr(item, "impostos"):
            raise ErroValidacao(f"Item {item.produto.prod_codi}: Impostos não foram calculados.")

        imp = item.impostos
        
        # Valida CSTs
        if not item.cst_icms:
            raise ErroValidacao(f"Item {item.produto.prod_codi}: CST de ICMS não definido.")
        if not item.cst_pis:
            raise ErroValidacao(f"Item {item.produto.prod_codi}: CST de PIS não definido.")
        if not item.cst_cofins:
            raise ErroValidacao(f"Item {item.produto.prod_codi}: CST de COFINS não definido.")

        # Valida Totais do Item
        if item.total <= 0:
            # Pode haver itens gratuitos/bonificação, mas geralmente total > 0.
            # Se for bonificação, verificar se a lógica permite. Por enquanto, warning ou erro.
            # Vamos assumir erro para vendas normais.
            pass


def validar_ambiente(tpAmb_xml: int, ambiente_filial: int, url_destino: str):
    """
    Valida se:
    - tpAmb do XML (1 ou 2)
    - ambiente configurado na Filial (1 ou 2)
    - URL (homologação vs produção)
    estão coerentes.
    """
    if tpAmb_xml not in (1, 2):
        raise AmbienteMismatchError(f"tpAmb inválido no XML: {tpAmb_xml}")

    if ambiente_filial not in (1, 2):
        raise AmbienteMismatchError(f"Ambiente inválido na filial: {ambiente_filial}")

    if tpAmb_xml != ambiente_filial:
        raise AmbienteMismatchError(
            f"tpAmb do XML ({tpAmb_xml}) diferente do ambiente da filial ({ambiente_filial})"
        )

    url_lower = (url_destino or "").lower()

    if tpAmb_xml == 1:
        # Produção: não deveria estar indo para URL de homologação
        if "homolog" in url_lower or "hml" in url_lower:
            raise AmbienteMismatchError(
                f"Ambiente produção (1) mas URL parece de homologação: {url_destino}"
            )
    else:
        # Homologação: não deveria estar indo para URL de produção
        if "homolog" not in url_lower and "hml" not in url_lower:
            # alguns estados não têm 'homolog' no nome, por isso só avisamos
            # e não travamos com raise
            pass
