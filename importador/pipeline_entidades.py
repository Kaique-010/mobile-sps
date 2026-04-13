from .services.leitor_xls import LeitorXLS
from .services.mapeamento_entidades import MapeamentoCamposEntidades
from .services.normalizadores_entidades import NormalizadoresEntidades
from .services.valida_entidade import ValidadorEntidade
from .services.upsert_entidade import UpsertEntidade


class ImportadorEntidadesPipeline:
    def __init__(self, file, empresa, db):
        self.file = file
        self.empresa = empresa
        self.db = db

    def processar(self):
        df = LeitorXLS(self.file).to_dataframe()
        df = MapeamentoCamposEntidades(df).mapear()
        df = NormalizadoresEntidades(df).aplicar()

        relatorio = {"criadas": 0, "atualizadas": 0, "erros": []}

        for idx, row in enumerate(df.to_dict("records"), start=2):
            try:
                ValidadorEntidade(row).validar()
                _, criado = UpsertEntidade(row, self.empresa, self.db).executar()
                if criado:
                    relatorio["criadas"] += 1
                else:
                    relatorio["atualizadas"] += 1
            except Exception as exc:
                relatorio["erros"].append(f"Linha {idx}: {str(exc)}")

        return relatorio
