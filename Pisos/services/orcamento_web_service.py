# Pisos/services/orcamento_web_service.py

from Pisos.models import Orcamentopisos
from Pisos.services.orcamento_criar_service import OrcamentoCriarService
from Pisos.services.orcamento_atualizar_service import OrcamentoAtualizarService


class OrcamentoWebService:

    @staticmethod
    def criar(*, banco, dados, itens):
        return OrcamentoCriarService().executar(
            banco=banco,
            dados=dados,
            itens=itens,
        )

    @staticmethod
    def atualizar(*, banco, orcamento_nume, dados, itens):
        orcamento = Orcamentopisos.objects.using(banco).get(
            orca_nume=orcamento_nume
        )

        return OrcamentoAtualizarService().executar(
            banco=banco,
            orcamento=orcamento,
            dados=dados,
            itens=itens,
        )