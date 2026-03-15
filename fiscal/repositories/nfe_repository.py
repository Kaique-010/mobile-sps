from fiscal.models import NFeDocumento


class NFeRepository:
    def __init__(self, *, banco: str):
        self.banco = banco or "default"

    def upsert_documento(self, *, empresa: int, filial: int, chave: str, tipo: str, xml_original: str, json_normalizado: str):
        obj, _ = NFeDocumento.objects.using(self.banco).update_or_create(
            empresa=int(empresa),
            filial=int(filial),
            chave=str(chave),
            defaults={
                "tipo": str(tipo),
                "xml_original": xml_original or "",
                "json_normalizado": json_normalizado or "{}",
            },
        )
        return obj

    def get_documento(self, documento_id: int):
        return NFeDocumento.objects.using(self.banco).get(pk=int(documento_id))

