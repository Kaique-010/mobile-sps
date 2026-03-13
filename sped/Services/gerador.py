from sped.Services.bloco0 import Bloco0Service
from sped.Services.bloco9 import Bloco9Service
from sped.Services.blocoC import BlocoCService
from sped.Services.blocoE import BlocoEService
from sped.Services.blocoG import BlocoGService
from sped.Services.blocoH import BlocoHService
from sped.Services.blocoK import BlocoKService


class GeradorSpedService:
    def __init__(self, *, db_alias, empresa_id, filial_id, data_inicio, data_fim, cod_receita=None, data_vencimento=None):
        self.db_alias = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.cod_receita = cod_receita
        self.data_vencimento = data_vencimento

    def gerar(self):
        linhas = []

        bloco0 = Bloco0Service(
            db_alias=self.db_alias,
            empresa_id=self.empresa_id,
            filial_id=self.filial_id,
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        ).gerar()
        linhas.extend(bloco0)

        blococ = BlocoCService(
            db_alias=self.db_alias,
            empresa_id=self.empresa_id,
            filial_id=self.filial_id,
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        ).gerar()
        linhas.extend(blococ)

        bloco_e = BlocoEService(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            linhas_blococ=blococ,
            cod_receita=self.cod_receita,
            data_vencimento=self.data_vencimento,
        ).gerar()
        linhas.extend(bloco_e)

        bloco_g = BlocoGService(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        ).gerar()
        linhas.extend(bloco_g)

        bloco_h = BlocoHService(
            db_alias=self.db_alias,
            empresa_id=self.empresa_id,
            filial_id=self.filial_id,
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        ).gerar()
        linhas.extend(bloco_h)

        bloco_k = BlocoKService(
            db_alias=self.db_alias,
            empresa_id=self.empresa_id,
            filial_id=self.filial_id,
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        ).gerar()
        linhas.extend(bloco_k)

        bloco9 = Bloco9Service(linhas_anteriores=linhas).gerar()
        linhas.extend(bloco9)

        return "\r\n".join(linhas) + "\r\n"
