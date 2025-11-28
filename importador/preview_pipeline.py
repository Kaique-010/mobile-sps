# importador_produtos/preview_pipeline.py

from .services.leitor_xls import LeitorXLS
from .services.mapeamento_campos import MapeamentoCampos


class PreviewImportadorPipeline:
    def __init__(self, file):
        self.file = file

    def gerar_preview(self):
        df = LeitorXLS(self.file).to_dataframe()

        # Determina colunas originais
        colunas_origem = list(df.columns)

        # Mapeamento automático (não altera DF ainda)
        mapper = MapeamentoCampos(df)
        colunas_mapeadas = [mapper.map_coluna(c) for c in colunas_origem]

        # Primeiras 10 linhas
        preview_linhas = df.head(10).to_dict("records")

        return {
            "colunas_origem": colunas_origem,
            "colunas_mapeadas": colunas_mapeadas,
            "preview_linhas": preview_linhas,
        }
