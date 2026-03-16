class DevolucaoEngine:

    CFOP_MAP = {
        "1": "5",
        "2": "6",
        "5": "1",
        "6": "2",
    }

    def processar_devolucao(self, doc_json: dict):

        itens = doc_json.get("itens") or []

        for item in itens:
            cfop = str(item.get("CFOP") or "")

            if cfop:
                item["cfop_devolucao"] = self._inverter_cfop(cfop)

        doc_json["itens"] = itens
        return doc_json

    def _inverter_cfop(self, cfop: str):

        if not cfop or len(cfop) != 4:
            return cfop

        return self.CFOP_MAP.get(cfop[0], cfop[0]) + cfop[1:]