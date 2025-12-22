class ErroDominio(Exception):
    def __init__(self, mensagem, codigo="erro_dominio", detalhes=None):
        self.mensagem = mensagem
        self.codigo = codigo
        self.detalhes = detalhes or {}
        super().__init__(mensagem)
