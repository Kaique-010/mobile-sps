class ErroEmissao(Exception):
    """
    Erro genérico de emissão de NF-e.
    Usamos para encapsular problemas de certificado, XML, SEFAZ etc.
    """
    pass


class AmbienteMismatchError(ErroEmissao):
    """
    Erro quando há inconsistência entre:
    - tpAmb do XML
    - ambiente configurado na filial
    - URL usada (homologação vs produção)
    """
    pass


class ErroValidacao(ErroEmissao):
    """
    Erro de validação de dados da nota fiscal (campos obrigatórios, regras de negócio).
    """
    pass