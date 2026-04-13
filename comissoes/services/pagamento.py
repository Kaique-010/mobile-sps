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
        centro_custo_id: int | None = None,
        banco_caixa_id: int | None = None,
    ) -> PagamentoComissao:
        if not itens:
            raise ValueError("Informe ao menos um item para pagamento.")

        beneficiario_id = int(beneficiario_id)
        cecu_id = int(centro_custo_id) if centro_custo_id not in (None, "", 0) else 0

        with transaction.atomic(using=self.db):
            pagamento = PagamentoComissao.objects.using(self.db).create(
                pagc_empr=self.empresa_id,
                pagc_fili=self.filial_id,
                pagc_data=data_pagamento,
                pagc_bene=beneficiario_id,
                pagc_valo=Decimal("0.00"),
                pagc_obse=observacao,
                pagc_cecu=cecu_id,
            )

            total_pagamento = Decimal("0.00")
            lancamentos_afetados: list[LancamentoComissao] = []
            totais_por_cecu: dict[int, Decimal] = {}

            for item in itens:
                lancamento_id = int(item.get("lancamento_id") or item.get("lcom_id") or 0)
                if not lancamento_id:
                    raise ValueError("Item sem lancamento_id.")

                lancamento = (
                    LancamentoComissao.objects.using(self.db)
                    .select_for_update()
                    .select_related("lcom_regra")
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

                try:
                    l_cecu = int(getattr(lancamento, "lcom_cecu", 0) or 0)
                except Exception:
                    l_cecu = 0
                try:
                    regra_cecu = int(getattr(getattr(lancamento, "lcom_regra", None), "regc_cecu", 0) or 0)
                except Exception:
                    regra_cecu = 0
                efetivo_cecu = l_cecu if l_cecu > 0 else (regra_cecu if regra_cecu > 0 else int(cecu_id or 0))

                PagamentoComissaoItem.objects.using(self.db).create(
                    pgci_paga=pagamento,
                    pgci_lanc=lancamento,
                    pgci_valo=valor_pagar,
                    pgci_cecu=efetivo_cecu,
                )

                if efetivo_cecu > 0:
                    totais_por_cecu[efetivo_cecu] = decimal_2(
                        (totais_por_cecu.get(efetivo_cecu) or Decimal("0.00")) + decimal_2(valor_pagar)
                    )

                total_pagamento += valor_pagar
                lancamentos_afetados.append(lancamento)

            if cecu_id in (None, "", 0) and len(totais_por_cecu) == 1:
                pagamento.pagc_cecu = int(next(iter(totais_por_cecu.keys())))

            pagamento.pagc_valo = decimal_2(total_pagamento)
            pagamento.save(using=self.db)

            for lancamento in lancamentos_afetados:
                self.atualizar_status_lancamento(lancamento_id=lancamento.lcom_id)

            if totais_por_cecu:
                self._criar_lancamentos_bancarios_saida(
                    pagamento=pagamento,
                    beneficiario_id=beneficiario_id,
                    totais_por_cecu=totais_por_cecu,
                    banco_caixa_id=banco_caixa_id,
                )

            return pagamento

    def _resolver_banco_caixa_saida(self, *, beneficiario_id: int, banco_caixa_id: int | None):
        try:
            from Entidades.models import Entidades
        except Exception:
            Entidades = None
        if not Entidades:
            raise ValueError("Módulo Entidades não disponível para resolver banco/caixa.")

        if banco_caixa_id not in (None, "", 0):
            banc = int(banco_caixa_id)
            existe = Entidades.objects.using(self.db).filter(enti_empr=self.empresa_id, enti_clie=banc).exists()
            if not existe:
                raise ValueError("Banco/caixa informado não existe para esta empresa.")
            return banc

        caixa = (
            Entidades.objects.using(self.db)
            .filter(enti_empr=self.empresa_id, enti_tien="C")
            .order_by("enti_clie")
            .first()
        )
        if caixa and getattr(caixa, "enti_clie", None) is not None:
            return int(caixa.enti_clie)

        banco = (
            Entidades.objects.using(self.db)
            .filter(enti_empr=self.empresa_id, enti_tien="B")
            .order_by("enti_clie")
            .first()
        )
        if banco and getattr(banco, "enti_clie", None) is not None:
            return int(banco.enti_clie)

        raise ValueError("Nenhum banco/caixa padrão configurado para esta empresa.")

    def _criar_lancamentos_bancarios_saida(
        self,
        *,
        pagamento: PagamentoComissao,
        beneficiario_id: int,
        totais_por_cecu: dict[int, Decimal],
        banco_caixa_id: int | None = None,
    ):
        try:
            from contas_a_pagar.models import Titulospagar
            from contas_a_pagar.services import baixar_titulo_pagar
        except Exception:
            raise ValueError("Módulo Contas a Pagar não disponível para criar baixa.")

        banc_id = self._resolver_banco_caixa_saida(beneficiario_id=beneficiario_id, banco_caixa_id=banco_caixa_id)

        for i, (cecu, total) in enumerate(sorted(totais_por_cecu.items(), key=lambda x: int(x[0])), start=1):
            total = decimal_2(total)
            if total <= Decimal("0.00"):
                continue
            
            titulo = Titulospagar.objects.using(self.db).create(
                titu_empr=self.empresa_id,
                titu_fili=self.filial_id,
                titu_forn=beneficiario_id,
                titu_titu=str(pagamento.pagc_id),
                titu_seri="COM",
                titu_parc=f"{i:03d}",
                titu_emis=pagamento.pagc_data,
                titu_venc=pagamento.pagc_data,
                titu_valo=total,
                titu_aber="A",
                titu_cecu=int(cecu),
                titu_hist=f"Pagamento de comissão #{pagamento.pagc_id}",
            )

            baixar_titulo_pagar(
                titulo=titulo,
                banco=self.db,
                dados={
                    "valor_pago": total,
                    "data_pagamento": pagamento.pagc_data,
                    "forma_pagamento": "B",
                    "banco": banc_id,
                    "historico": f"Pagamento de comissão #{pagamento.pagc_id}",
                }
            )

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
