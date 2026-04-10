from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction

from comissoes.models import RegraComissao
from comissoes.services.utils import decimal_2


class CadastroComissaoService:
    def __init__(self, *, db_alias: str, empresa_id: int, filial_id: int):
        self.db = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)

    def listar_regras(self, *, beneficiario_id: int | None = None, ativas: bool | None = None):
        qs = RegraComissao.objects.using(self.db).filter(
            regc_empr=self.empresa_id,
            regc_fili=self.filial_id,
        )
        if beneficiario_id is not None:
            qs = qs.filter(regc_bene=int(beneficiario_id))
        if ativas is not None:
            qs = qs.filter(regc_ativ=bool(ativas))
        return qs.order_by("regc_id")

    def salvar_regra(
        self,
        *,
        beneficiario_id: int,
        percentual: Decimal,
        ativo: bool = True,
        data_ini: date | None = None,
        data_fim: date | None = None,
    ) -> RegraComissao:
        percentual = decimal_2(percentual)

        with transaction.atomic(using=self.db):
            regra, _ = RegraComissao.objects.using(self.db).update_or_create(
                regc_empr=self.empresa_id,
                regc_fili=self.filial_id,
                regc_bene=int(beneficiario_id),
                regc_data_ini=data_ini,
                regc_data_fim=data_fim,
                defaults={
                    "regc_perc": percentual,
                    "regc_ativ": bool(ativo),
                },
            )
            return regra

    def obter_regra(self, *, regra_id: int) -> RegraComissao | None:
        return (
            RegraComissao.objects.using(self.db)
            .filter(
                regc_id=int(regra_id),
                regc_empr=self.empresa_id,
                regc_fili=self.filial_id,
            )
            .first()
        )

    def atualizar_regra(
        self,
        *,
        regra_id: int,
        beneficiario_id: int,
        percentual: Decimal,
        ativo: bool = True,
        data_ini: date | None = None,
        data_fim: date | None = None,
    ) -> RegraComissao:
        percentual = decimal_2(percentual)

        with transaction.atomic(using=self.db):
            regra = self.obter_regra(regra_id=int(regra_id))
            if not regra:
                raise ValueError("Regra não encontrada.")

            regra.regc_bene = int(beneficiario_id)
            regra.regc_perc = percentual
            regra.regc_ativ = bool(ativo)
            regra.regc_data_ini = data_ini
            regra.regc_data_fim = data_fim
            regra.save(using=self.db)
            return regra

    def ativar_regra(self, *, regra_id: int) -> int:
        return (
            RegraComissao.objects.using(self.db)
            .filter(
                regc_id=int(regra_id),
                regc_empr=self.empresa_id,
                regc_fili=self.filial_id,
            )
            .update(regc_ativ=True)
        )

    def desativar_regra(self, *, regra_id: int) -> int:
        return (
            RegraComissao.objects.using(self.db)
            .filter(
                regc_id=int(regra_id),
                regc_empr=self.empresa_id,
                regc_fili=self.filial_id,
            )
            .update(regc_ativ=False)
        )
