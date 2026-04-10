from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from comissoes.models import LancamentoComissao, PagamentoComissao, PagamentoComissaoItem
from comissoes.services.utils import decimal_2


class PagamentoComissaoService:
    def __init__(self, *, db_alias: str, empresa_id: int, filial_id: int):
        self.db = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)

    def comissoes_em_aberto(self, *, beneficiario_id: int | None = None):
        qs = LancamentoComissao.objects.using(self.db).filter(
            lcom_empr=self.empresa_id,
            lcom_fili=self.filial_id,
            lcom_stat__in=[LancamentoComissao.STATUS_ABERTO, LancamentoComissao.STATUS_PARCIAL],
        )
        if beneficiario_id is not None:
            qs = qs.filter(lcom_bene=int(beneficiario_id))
        return qs.order_by("lcom_data", "lcom_id")

    def total_pago_lancamento(self, *, lancamento_id: int) -> Decimal:
        total = (
            PagamentoComissaoItem.objects.using(self.db)
            .filter(pgci_lanc_id=int(lancamento_id))
            .aggregate(total=Sum("pgci_valo"))
            .get("total")
        )
        return decimal_2(total or Decimal("0.00"))

    def saldo_lancamento(self, *, lancamento: LancamentoComissao) -> Decimal:
        total_pago = self.total_pago_lancamento(lancamento_id=lancamento.lcom_id)
        saldo = decimal_2(decimal_2(lancamento.lcom_valo) - total_pago)
        if saldo < Decimal("0.00"):
            saldo = Decimal("0.00")
        return saldo

    def gerar_pagamento(
        self,
        *,
        beneficiario_id: int,
        data_pagamento: date,
        itens: list[dict],
        observacao: str | None = None,
    ) -> PagamentoComissao:
        if not itens:
            raise ValueError("Informe ao menos um item para pagamento.")

        beneficiario_id = int(beneficiario_id)

        with transaction.atomic(using=self.db):
            pagamento = PagamentoComissao.objects.using(self.db).create(
                pagc_empr=self.empresa_id,
                pagc_fili=self.filial_id,
                pagc_data=data_pagamento,
                pagc_bene=beneficiario_id,
                pagc_valo=Decimal("0.00"),
                pagc_obse=observacao,
            )

            total_pagamento = Decimal("0.00")
            lancamentos_afetados: list[LancamentoComissao] = []

            for item in itens:
                lancamento_id = int(item.get("lancamento_id") or item.get("lcom_id") or 0)
                if not lancamento_id:
                    raise ValueError("Item sem lancamento_id.")

                lancamento = (
                    LancamentoComissao.objects.using(self.db)
                    .select_for_update()
                    .filter(
                        lcom_id=lancamento_id,
                        lcom_empr=self.empresa_id,
                        lcom_fili=self.filial_id,
                        lcom_bene=beneficiario_id,
                    )
                    .first()
                )
                if not lancamento:
                    raise ValueError(f"Lançamento não encontrado: {lancamento_id}")

                saldo = self.saldo_lancamento(lancamento=lancamento)
                if saldo <= Decimal("0.00"):
                    continue

                valor_informado = item.get("valor") if "valor" in item else None
                valor_pagar = saldo if valor_informado is None else decimal_2(valor_informado)
                if valor_pagar <= Decimal("0.00"):
                    continue
                if valor_pagar > saldo:
                    raise ValueError(
                        f"Valor do pagamento ({valor_pagar}) maior que saldo ({saldo}) para lançamento {lancamento_id}."
                    )

                PagamentoComissaoItem.objects.using(self.db).create(
                    pgci_paga=pagamento,
                    pgci_lanc=lancamento,
                    pgci_valo=valor_pagar,
                )

                total_pagamento += valor_pagar
                lancamentos_afetados.append(lancamento)

            pagamento.pagc_valo = decimal_2(total_pagamento)
            pagamento.save(using=self.db)

            for lancamento in lancamentos_afetados:
                self.atualizar_status_lancamento(lancamento_id=lancamento.lcom_id)

            return pagamento

    def atualizar_status_lancamento(self, *, lancamento_id: int) -> int:
        lancamento = (
            LancamentoComissao.objects.using(self.db)
            .filter(
                lcom_id=int(lancamento_id),
                lcom_empr=self.empresa_id,
                lcom_fili=self.filial_id,
            )
            .first()
        )
        if not lancamento:
            return 0

        total_pago = self.total_pago_lancamento(lancamento_id=lancamento.lcom_id)
        total_devido = decimal_2(lancamento.lcom_valo)

        if total_pago >= total_devido and total_devido > Decimal("0.00"):
            novo_status = LancamentoComissao.STATUS_PAGO
        elif total_pago > Decimal("0.00"):
            novo_status = LancamentoComissao.STATUS_PARCIAL
        else:
            novo_status = LancamentoComissao.STATUS_ABERTO

        if lancamento.lcom_stat == novo_status:
            return 0

        return (
            LancamentoComissao.objects.using(self.db)
            .filter(lcom_id=lancamento.lcom_id)
            .update(lcom_stat=novo_status)
        )
