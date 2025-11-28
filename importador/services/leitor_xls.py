# importador_produtos/services/leitor_xls.py
import pandas as pd


class LeitorXLS:
    def __init__(self, file):
        self.file = file

    def to_dataframe(self):
        name = getattr(self.file, "name", "") or ""
        lower = name.lower()
        try:
            if lower.endswith(".csv"):
                df = pd.read_csv(self.file, dtype=str)
            else:
                df = pd.read_excel(self.file, dtype=str)
        except Exception:
            if lower.endswith(".csv"):
                df = pd.read_csv(self.file, dtype=str, sep=";")
            else:
                df = pd.read_excel(self.file, dtype=str, engine="openpyxl")
        df = df.fillna("")
        return df
