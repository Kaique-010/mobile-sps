from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from comissoes.models import LancamentoComissao, RegraComissao
from comissoes.services.utils import decimal_2


class GeracaoComissaoService:
    def __init__(self, *, db_alias: str, empresa_id: int, filial_id: int):
        self.db = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)

    def regras_validas(self, *, data_ref: date, beneficiario_id: int | None = None):
        qs = RegraComissao.objects.using(self.db).filter(
            regc_empr=self.empresa_id,
            regc_fili=self.filial_id,
            regc_ativ=True,
        )
        qs = qs.filter(Q(regc_data_ini__isnull=True) | Q(regc_data_ini__lte=data_ref))
        qs = qs.filter(Q(regc_data_fim__isnull=True) | Q(regc_data_fim__gte=data_ref))
        if beneficiario_id is not None:
            qs = qs.filter(regc_bene=int(beneficiario_id))
        return qs.order_by("regc_id")

    def gerar_para_documento(
        self,
        *,
        tipo_origem: str,
        documento: str,
        data_doc: date,
        base: Decimal,
        centro_custo_id: int | None = None,
    ) -> list[LancamentoComissao]:
        tipo_origem = str(tipo_origem or "").strip()
        documento = str(documento or "").strip()
        base = decimal_2(base)

        if not tipo_origem:
            raise ValueError("Tipo de origem é obrigatório.")
        if not documento:
            raise ValueError("Documento é obrigatório.")

        regras = list(self.regras_validas(data_ref=data_doc))
        if not regras:
            return []

        resultado: list[LancamentoComissao] = []
        with transaction.atomic(using=self.db):
            for regra in regras:
                lanc = self._gerar_lancamento(
                    regra=regra,
                    tipo_origem=tipo_origem,
                    documento=documento,
                    data_doc=data_doc,
                    base=base,
                    centro_custo_id=centro_custo_id,
                )
                if lanc:
                    resultado.append(lanc)
        return resultado

    def gerar_para_documento_beneficiario(
        self,
        *,
        tipo_origem: str,
        documento: str,
        data_doc: date,
        base: Decimal,
        beneficiario_id: int,
        centro_custo_id: int | None = None,
    ) -> list[LancamentoComissao]:
        tipo_origem = str(tipo_origem or "").strip()
        documento = str(documento or "").strip()
        base = decimal_2(base)

        if not tipo_origem:
            raise ValueError("Tipo de origem é obrigatório.")
        if not documento:
            raise ValueError("Documento é obrigatório.")

        regras = list(self.regras_validas(data_ref=data_doc, beneficiario_id=int(beneficiario_id)))
        if not regras:
            return []

        resultado: list[LancamentoComissao] = []
        with transaction.atomic(using=self.db):
            for regra in regras:
                lanc = self._gerar_lancamento(
                    regra=regra,
                    tipo_origem=tipo_origem,
                    documento=documento,
                    data_doc=data_doc,
                    base=base,
                    centro_custo_id=centro_custo_id,
                )
                if lanc:
                    resultado.append(lanc)
        return resultado

    def _gerar_lancamento(
        self,
        *,
        regra: RegraComissao,
        tipo_origem: str,
        documento: str,
        data_doc: date,
        base: Decimal,
        centro_custo_id: int | None = None,
    ) -> LancamentoComissao | None:
        perc = decimal_2(regra.regc_perc)
        valo = decimal_2((base * perc) / Decimal("100.00"))
        cecu_regra = getattr(regra, "regc_cecu", None)
        cecu_id = int(cecu_regra) if cecu_regra not in (None, "", 0) else int(centro_custo_id or 0)

        qs = LancamentoComissao.objects.using(self.db).filter(
            lcom_empr=self.empresa_id,
            lcom_fili=self.filial_id,
            lcom_bene=int(regra.regc_bene),
            lcom_tipo_origem=tipo_origem,
            lcom_docu=documento,
        )
        existente = qs.first()
        if existente:
            if existente.lcom_stat != LancamentoComissao.STATUS_ABERTO:
                return existente
            existente.lcom_regra = regra
            existente.lcom_data = data_doc
            existente.lcom_base = base
            existente.lcom_perc = perc
            existente.lcom_valo = valo
            existente.lcom_cecu = cecu_id
            existente.save(using=self.db)
            return existente

        return LancamentoComissao.objects.using(self.db).create(
            lcom_empr=self.empresa_id,
            lcom_fili=self.filial_id,
            lcom_regra=regra,
            lcom_bene=int(regra.regc_bene),
            lcom_data=data_doc,
            lcom_tipo_origem=tipo_origem,
            lcom_docu=documento,
            lcom_base=base,
            lcom_perc=perc,
            lcom_valo=valo,
            lcom_stat=LancamentoComissao.STATUS_ABERTO,
            lcom_cecu=cecu_id,
        )
