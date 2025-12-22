from .excecoes import ErroDominio

class Ordem:
    """
    Representa as regras da Ordem de Serviço.
    """

    def __init__(self, prioridade):
        if prioridade < 0:
            raise ErroDominio(
                mensagem="Prioridade inválida",
                detalhes={"prioridade": "não pode ser negativa"}
            )
        self.prioridade = prioridade

    def alterar_prioridade(self, nova_prioridade):
        if nova_prioridade < 0:
            raise ErroDominio(
                mensagem="Nova prioridade inválida",
                detalhes={"prioridade": "não pode ser negativa"}
            )
        self.prioridade = nova_prioridade
