import re


class NormalizadoresEntidades:
    def __init__(self, df):
        self.df = df

    def _first_not_empty(self, values):
        for v in values:
            s = str(v or "").strip()
            if s:
                return s
        return ""

    def _digits(self, value, max_len=None):
        raw = re.sub(r"\D", "", str(value or ""))
        return raw[:max_len] if max_len else raw

    def aplicar(self):
        campos_base = [
            "enti_clie", "enti_nome", "enti_fant", "enti_tipo_enti", "enti_cpf", "enti_cnpj", "enti_insc_esta",
            "enti_cep", "enti_ende", "enti_nume", "enti_cida", "enti_esta", "enti_bair", "enti_comp",
            "enti_fone", "enti_celu", "enti_emai", "enti_situ",
        ]
        for campo in campos_base:
            duplicadas = [c for c in self.df.columns if c == campo or c.startswith(f"{campo}__")]
            if len(duplicadas) <= 1:
                continue
            self.df[campo] = self.df[duplicadas].apply(lambda row: self._first_not_empty(row), axis=1)
            for col in duplicadas:
                if col != campo:
                    self.df.drop(columns=[col], inplace=True)

        for col in ["enti_nome", "enti_fant", "enti_ende", "enti_cida", "enti_bair", "enti_comp", "enti_emai"]:
            if col in self.df:
                self.df[col] = self.df[col].apply(lambda v: str(v or "").strip())

        if "enti_esta" in self.df:
            self.df["enti_esta"] = self.df["enti_esta"].apply(lambda v: str(v or "").strip().upper()[:2])

        if "enti_tipo_enti" in self.df:
            mapa_tipo = {
                "cliente": "CL", "fornecedor": "FO", "ambos": "AM", "outros": "OU", "vendedor": "VE", "funcionarios": "FU",
            }
            self.df["enti_tipo_enti"] = self.df["enti_tipo_enti"].apply(
                lambda v: mapa_tipo.get(str(v or "").strip().lower(), str(v or "").strip().upper()[:2] or "CL")
            )

        if "enti_situ" in self.df:
            self.df["enti_situ"] = self.df["enti_situ"].apply(
                lambda v: "1" if str(v or "").strip().lower() in {"1", "ativo", "a", "sim", "s", "true"} else "0"
            )

        if "enti_cpf" in self.df:
            self.df["enti_cpf"] = self.df["enti_cpf"].apply(lambda v: self._digits(v, 11))
        if "enti_cnpj" in self.df:
            self.df["enti_cnpj"] = self.df["enti_cnpj"].apply(lambda v: self._digits(v, 14))
        if "enti_cep" in self.df:
            self.df["enti_cep"] = self.df["enti_cep"].apply(lambda v: self._digits(v, 8))
        if "enti_fone" in self.df:
            self.df["enti_fone"] = self.df["enti_fone"].apply(lambda v: self._digits(v, 14))
        if "enti_celu" in self.df:
            self.df["enti_celu"] = self.df["enti_celu"].apply(lambda v: self._digits(v, 15))

        return self.df
