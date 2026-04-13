
class ValidadorEntidade:
    def __init__(self, row):
        self.row = row

    def validar(self):
        if not self.row.get("enti_nome"):
            raise ValueError("Entidade sem nome")

        if not self.row.get("enti_ende"):
            self.row["enti_ende"] = "NÃO INFORMADO"
        if not self.row.get("enti_nume"):
            self.row["enti_nume"] = "S/N"
        if not self.row.get("enti_cida"):
            self.row["enti_cida"] = "NÃO INFORMADA"
        if not self.row.get("enti_bair"):
            self.row["enti_bair"] = "NÃO INFORMADO"
        if not self.row.get("enti_esta"):
            self.row["enti_esta"] = "TO"
        if not self.row.get("enti_cep"):
            self.row["enti_cep"] = "00000000"

        self.row["enti_tipo_enti"] = self.row.get("enti_tipo_enti") or "CL"
        self.row["enti_situ"] = self.row.get("enti_situ") or "1"
        self.row["enti_pais"] = self.row.get("enti_pais") or "1058"
        self.row["enti_codi_pais"] = self.row.get("enti_codi_pais") or "1058"
        self.row["enti_codi_cida"] = self.row.get("enti_codi_cida") or "0000000"

        return True
