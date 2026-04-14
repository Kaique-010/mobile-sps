from .services.leitor_xls import LeitorXLS
from .services.mapeamento_entidades import MapeamentoCamposEntidades


class PreviewImportadorEntidadesPipeline:
    def __init__(self, file):
        self.file = file

    def gerar_preview(self):
        df = LeitorXLS(self.file).to_dataframe()
        colunas_origem = list(df.columns)
        mapper = MapeamentoCamposEntidades(df.copy())
        df_map = mapper.mapear()
        colunas_mapeadas = list(df_map.columns)

        return {
            "colunas_origem": colunas_origem,
            "colunas_mapeadas": colunas_mapeadas,
            "preview_linhas": df.head(10).to_dict("records"),
        }
