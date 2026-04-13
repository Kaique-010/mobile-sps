import csv
from io import StringIO

import pandas as pd


class LeitorXLS:
    def __init__(self, file):
        self.file = file

    def _reset_file(self):
        if hasattr(self.file, "seek"):
            self.file.seek(0)

    def _normalize_dataframe(self, df):
        if df is None:
            return pd.DataFrame()

        df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
        df = df.fillna("")
        df = df.applymap(lambda value: str(value).strip() if value is not None else "")
        df = df.loc[:, [col for col in df.columns if col]]
        df = df[(df != "").any(axis=1)]
        return df.reset_index(drop=True)

    def _ler_csv(self):
        self._reset_file()
        raw = self.file.read()
        if isinstance(raw, bytes):
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    text = raw.decode(enc)
                    break
                except Exception:
                    text = None
            if text is None:
                text = raw.decode("utf-8", errors="ignore")
        else:
            text = str(raw or "")
        sample = text[:4096]
        delimiter = ";"
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            delimiter = getattr(dialect, "delimiter", ";") or ";"
        except Exception:
            for cand in (";", ",", "\t", "|"):
                if sample.count(cand) > 0:
                    delimiter = cand
                    break
        return pd.read_csv(StringIO(text), dtype=str, sep=delimiter, engine="python")

    def _ler_excel(self):
        self._reset_file()
        try:
            return pd.read_excel(self.file, dtype=str)
        except Exception:
            self._reset_file()
            return pd.read_excel(self.file, dtype=str, engine="openpyxl")

    def to_dataframe(self):
        name = getattr(self.file, "name", "") or ""
        lower = name.lower()
        try:
            if lower.endswith(".csv"):
                df = self._ler_csv()
            else:
                df = self._ler_excel()
        except Exception as exc:
            raise ValueError(f"Não foi possível ler o arquivo '{name}'. Verifique formato e conteúdo.") from exc
        return self._normalize_dataframe(df)
