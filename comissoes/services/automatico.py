from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction

from comissoes.models import LancamentoComissao
from comissoes.services.geracao import GeracaoComissaoService
from comissoes.services.utils import decimal_2


class ComissaoAutomaticaService:
    def __init__(self, *, db_alias: str, empresa_id: int, filial_id: int):
        self.db = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)
        self.geracao = GeracaoComissaoService(db_alias=db_alias, empresa_id=empresa_id, filial_id=filial_id)

    def gerar_por_documento(
        self,
        *,
        tipo_origem: str,
        documento: str,
        data_doc: date,
        base: Decimal,
        beneficiario_id: int | None,
    ) -> list[LancamentoComissao]:
        bene = int(beneficiario_id or 0)
        if bene <= 0:
            return []

        base = decimal_2(base)
        if base <= Decimal("0.00"):
            return []

        with transaction.atomic(using=self.db):
            lancs = self.geracao.gerar_para_documento_beneficiario(
                tipo_origem=tipo_origem,
                documento=documento,
                data_doc=data_doc,
                base=base,
                beneficiario_id=bene,
            )
            (
                LancamentoComissao.objects.using(self.db)
                .filter(
                    lcom_empr=self.empresa_id,
                    lcom_fili=self.filial_id,
                    lcom_tipo_origem=tipo_origem,
                    lcom_docu=documento,
                )
                .exclude(lcom_bene=bene)
                .filter(lcom_stat__in=[LancamentoComissao.STATUS_ABERTO, LancamentoComissao.STATUS_PARCIAL])
                .update(lcom_stat=LancamentoComissao.STATUS_CANCELADO)
            )
            return lancs

    def gerar_por_pedido(self, *, pedido) -> list[LancamentoComissao]:
        bene = _to_int(getattr(pedido, "pedi_vend", None))
        return self.gerar_por_documento(
            tipo_origem="pedido",
            documento=str(getattr(pedido, "pedi_nume", "") or "").strip(),
            data_doc=getattr(pedido, "pedi_data", None) or date.today(),
            base=getattr(pedido, "pedi_tota", None) or Decimal("0.00"),
            beneficiario_id=bene,
        )


def _to_int(valor) -> int | None:
    if valor is None:
        return None
    s = str(valor).strip()
    if not s:
        return None
    head = s.split("-", 1)[0].strip()
    if head.isdigit():
        return int(head)
    if s.isdigit():
        return int(s)
    return None
