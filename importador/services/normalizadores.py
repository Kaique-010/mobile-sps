# importador_produtos/services/normalizadores.py
import re


class Normalizadores:
    def __init__(self, df):
        self.df = df

    def normalizar_texto(self, txt):
        if not txt:
            return ""
        return str(txt).strip()

    def normalizar_ncm(self, ncm):
        if not ncm:
            return ""
        n = re.sub(r'\D', '', str(ncm))
        if len(n) > 8:
            n = n[:8]
        return n

    def aplicar(self):
        # Consolidar colunas duplicadas mapeadas como <campo>__2, <campo>__3...
        for base_col in ["prod_nome", "prod_ncm", "prod_gtin", "prod_marc", "prod_grup", "prod_sugr", "prod_fami", "prod_unme", "prod_loca", "prod_orig_merc", "preco", "preco_compra", "preco_vista", "preco_prazo"]:
            duplicadas = [c for c in self.df.columns if c == base_col or c.startswith(f"{base_col}__")]
            if len(duplicadas) <= 1:
                continue
            self.df[base_col] = self.df[duplicadas].apply(
                lambda row: next((str(v).strip() for v in row if str(v or "").strip()), ""),
                axis=1,
            )
            for col in duplicadas:
                if col != base_col:
                    self.df.drop(columns=[col], inplace=True)

        if "prod_nome" in self.df:
            self.df["prod_nome"] = self.df["prod_nome"].apply(self.normalizar_texto)
        else:
            # Fallback: tenta encontrar colunas possíveis e promovê-las a prod_nome
            for candidate in [
                "descricao do item", "descrição do item", "descricao", "descrição", "produto", "nome"
            ]:
                if candidate in self.df:
                    self.df["prod_nome"] = self.df[candidate].apply(self.normalizar_texto)
                    break

        if "prod_ncm" in self.df:
            self.df["prod_ncm"] = self.df["prod_ncm"].apply(self.normalizar_ncm)

        def _norm_price(v):
            s = str(v or "").strip()
            if not s:
                return 0.0
            s = s.replace(".", "").replace(",", ".")
            s = re.sub(r"[^0-9\.]", "", s)
            try:
                return float(s or 0)
            except Exception:
                return 0.0
        for col in ["preco", "preco_compra", "preco_vista", "preco_prazo"]:
            if col in self.df:
                self.df[col] = self.df[col].apply(_norm_price)

        return self.df
