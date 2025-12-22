from .excecoes import ErroDominio

class Pedido:
    """
    Representa as regras do Pedido.
    """

    def __init__(self, status):
        if status < 0:
            raise ErroDominio(
                mensagem="Status inválido",
                detalhes={"status": "não pode ser negativo"}
            )
        self.status = status

    def alterar_status(self, novo_status):
        if novo_status < 0:
            raise ErroDominio(
                mensagem="Novo status inválido",
                detalhes={"status": "não pode ser negativo"}
            )
        self.status = novo_status
