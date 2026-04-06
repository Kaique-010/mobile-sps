import re

from django.core.exceptions import ValidationError

from fiscal.models import NFeDocumento


class EntradaXMLService:
    def __init__(self, *, banco: str):
        self.banco = banco or "default"

    def processar(self, *, empresa: int, filial: int, documento_id: int, usuario_id: int = 0) -> dict:
        doc = (
            NFeDocumento.objects.using(self.banco)
            .filter(pk=int(documento_id), empresa=int(empresa), filial=int(filial))
            .first()
        )
        if not doc:
            raise ValidationError("Documento não encontrado.")

        xml = (doc.xml_original or "").strip()
        if not xml:
            raise ValidationError("Documento não possui XML.")

        try:
            from NotasDestinadas.services.entrada_nfe_service import EntradaNFeService
        except Exception:
            raise ValidationError("Serviço de entrada (NotasDestinadas) não está disponível.")

        nota = EntradaNFeService.registrar_entrada(
            xml=xml,
            empresa=int(empresa),
            filial=int(filial),
            banco=self.banco,
            usuario_id=int(usuario_id or 0),
        )

        itens = EntradaNFeService.listar_itens(nota) or []
        entradas = []
        for item in itens:
            if not isinstance(item, dict):
                continue
            prod = self._auto_map_produto(empresa=int(empresa), item=item)
            payload = dict(item)
            payload["prod"] = prod
            entradas.append(payload)

        resultado = EntradaNFeService.confirmar_processamento(
            nota,
            entradas,
            banco=self.banco,
            usuario_id=int(usuario_id or 0),
        )
        if not isinstance(resultado, dict):
            resultado = {"status": "sucesso"}

        out = {
            "nota_entrada_id": getattr(nota, "id", None),
            "empresa": getattr(nota, "empresa", None),
            "filial": getattr(nota, "filial", None),
            "serie": getattr(nota, "serie", None),
            "numero_nota_fiscal": getattr(nota, "numero_nota_fiscal", None),
        }
        out.update(resultado)
        return out

    def _auto_map_produto(self, *, empresa: int, item: dict):
        try:
            from Produtos.models import Produtos
        except Exception:
            return None

        base = Produtos.objects.using(self.banco).filter(prod_empr=str(empresa))

        ean = _only_digits(item.get("ean"))
        forn_cod = str(item.get("forn_cod") or "").strip()
        forn_digits = _only_digits(forn_cod)

        candidates = []
        if ean:
            candidates.extend(
                [
                    base.filter(prod_gtin=ean),
                    base.filter(prod_coba=ean),
                ]
            )
        if forn_cod:
            candidates.extend(
                [
                    base.filter(prod_codi=forn_cod),
                    base.filter(prod_codi_nume=forn_cod),
                    base.filter(prod_coba=forn_cod),
                ]
            )
        if forn_digits and forn_digits != forn_cod:
            candidates.extend(
                [
                    base.filter(prod_codi=forn_digits),
                    base.filter(prod_codi_nume=forn_digits),
                    base.filter(prod_coba=forn_digits),
                ]
            )

        for qs in candidates:
            code = _unique_code(qs)
            if code:
                return code

        return None


def _unique_code(qs):
    try:
        codes = list(qs.values_list("prod_codi", flat=True)[:2])
    except Exception:
        return None
    if len(codes) == 1:
        return codes[0]
    return None


def _only_digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))
