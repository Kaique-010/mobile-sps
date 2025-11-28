# importador_produtos/pipeline.py
import pandas as pd
from .services.leitor_xls import LeitorXLS
from .services.mapeamento_campos import MapeamentoCampos
from .services.normalizadores import Normalizadores
from .services.resolvers_fk import ResolvedorFK
from .services.valida_produto import ValidadorProduto
from .services.upsert_produto import UpsertProduto
from .services.upsert_precos import UpsertPrecos


class ImportadorProdutosPipeline:
    def __init__(self, file, empresa, filial, db):
        self.file = file
        self.empresa = empresa
        self.filial = filial
        self.db = db

    def processar(self):
        # 1) Leitura XLS
        df = LeitorXLS(self.file).to_dataframe()

        # 2) Mapeamento Excel → campos ORM
        df = MapeamentoCampos(df).mapear()

        # 3) Normalização dos dados
        df = Normalizadores(df).aplicar()

        relatorio = {
            "criadas": 0,
            "atualizadas": 0,
            "precos": 0,
            "erros": [],
            "duplicatas_arquivo": 0,
            "nomes_duplicados": []
        }

        import unicodedata, re
        nomes_vistos = set()
        def chave_nome(x):
            s = str(x or "").strip().lower()
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(c for c in s if not unicodedata.combining(c))
            s = re.sub(r"\s+", " ", s)
            return s
        for row in df.to_dict("records"):
            try:
                # 4) Resolver FKs
                resolved = ResolvedorFK(row, self.db).resolver()

                # 5) Validar
                ValidadorProduto(resolved).validar()
                chave = chave_nome(resolved.get("prod_nome"))
                if not chave:
                    raise ValueError("Produto sem nome")
                if chave in nomes_vistos:
                    relatorio["duplicatas_arquivo"] += 1
                    relatorio["nomes_duplicados"].append(resolved.get("prod_nome") or "")
                    raise ValueError("Descricao duplicada no arquivo")
                nomes_vistos.add(chave)

                # 6) Criar/Atualizar Produto
                prod, criado = UpsertProduto(resolved, self.empresa, self.db).executar()

                # 7) Criar/Atualizar Preço
                UpsertPrecos(prod, resolved, self.empresa, self.filial, self.db).executar()

                if criado:
                    relatorio["criadas"] += 1
                else:
                    relatorio["atualizadas"] += 1

                relatorio["precos"] += 1

            except Exception as e:
                relatorio["erros"].append(str(e))

        return relatorio
