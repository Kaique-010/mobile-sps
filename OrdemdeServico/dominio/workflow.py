from .excecoes import ErroDominio

class WorkflowOrdem:
    """
    Regras de transição de setores.
    """

    def __init__(self, setor_atual):
        self.setor_atual = setor_atual

    def validar_avanco(self, setor_destino, setores_permitidos):
        if setor_destino not in setores_permitidos:
            raise ErroDominio(
                mensagem="Transição de setor inválida",
                codigo="workflow_invalido",
                detalhes={
                    "setor_atual": self.setor_atual,
                    "setor_destino": setor_destino,
                    "permitidos": setores_permitidos,
                }
            )
