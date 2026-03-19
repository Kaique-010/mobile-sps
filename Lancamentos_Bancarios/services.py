from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

from .models import Lctobancario
from .utils import get_next_lcto_number


def criar_lancamento(*, banco: str, dados: Dict[str, Any]) -> Lctobancario:
    dados = dict(dados)
    allowed_fields = {f.name for f in Lctobancario._meta.fields}
    dados = {k: v for k, v in dados.items() if k in allowed_fields}

    obrigatorios = ["laba_empr", "laba_fili", "laba_banc", "laba_data", "laba_valo", "laba_dbcr"]
    faltando = [k for k in obrigatorios if dados.get(k) in (None, "")]
    if faltando:
        raise ValidationError({"detail": [f"Campos obrigatórios: {', '.join(faltando)}."]})

    dbcr = str(dados.get("laba_dbcr") or "").strip().upper()
    if dbcr not in ("C", "D"):
        raise ValidationError({"detail": ["laba_dbcr deve ser 'C' (entrada) ou 'D' (saída)."]})

    with transaction.atomic(using=banco):
        dados["laba_dbcr"] = dbcr
        dados["laba_ctrl"] = get_next_lcto_number(int(dados["laba_empr"]), int(dados["laba_fili"]), banco)
        return Lctobancario.objects.using(banco).create(**dados)

def criar_entrada(*, banco: str, dados: Dict[str, Any]) -> Lctobancario:
    dados = dict(dados)
    dados["laba_dbcr"] = "C"
    return criar_lancamento(banco=banco, dados=dados)


def criar_saida(*, banco: str, dados: Dict[str, Any]) -> Lctobancario:
    dados = dict(dados)
    dados["laba_dbcr"] = "D"
    return criar_lancamento(banco=banco, dados=dados)


def atualizar_lancamento(*, banco: str, laba_ctrl: int, dados: Dict[str, Any]) -> Lctobancario:
    obj = Lctobancario.objects.using(banco).filter(laba_ctrl=int(laba_ctrl)).first()
    if not obj:
        raise ValidationError({"detail": ["Lançamento não encontrado."]})

    permitidos = {"laba_banc", "laba_data", "laba_cecu", "laba_valo", "laba_hist", "laba_enti"}
    updates = {k: v for k, v in dict(dados).items() if k in permitidos}
    updates.pop("laba_dbcr", None)
    updates.pop("laba_ctrl", None)

    if not updates:
        raise ValidationError({"detail": ["Nenhum campo para atualizar."]})

    with transaction.atomic(using=banco):
        Lctobancario.objects.using(banco).filter(laba_ctrl=int(laba_ctrl)).update(**updates)
        return Lctobancario.objects.using(banco).get(laba_ctrl=int(laba_ctrl))


def atualizar_entrada(*, banco: str, laba_ctrl: int, dados: Dict[str, Any]) -> Lctobancario:
    obj = Lctobancario.objects.using(banco).filter(laba_ctrl=int(laba_ctrl)).first()
    if not obj:
        raise ValidationError({"detail": ["Lançamento não encontrado."]})
    if (obj.laba_dbcr or "").upper() != "C":
        raise ValidationError({"detail": ["Lançamento não é do tipo entrada."]})
    dados = dict(dados)
    dados["laba_dbcr"] = "C"
    return atualizar_lancamento(banco=banco, laba_ctrl=laba_ctrl, dados=dados)


def atualizar_saida(*, banco: str, laba_ctrl: int, dados: Dict[str, Any]) -> Lctobancario:
    obj = Lctobancario.objects.using(banco).filter(laba_ctrl=int(laba_ctrl)).first()
    if not obj:
        raise ValidationError({"detail": ["Lançamento não encontrado."]})
    if (obj.laba_dbcr or "").upper() != "D":
        raise ValidationError({"detail": ["Lançamento não é do tipo saída."]})
    dados = dict(dados)
    dados["laba_dbcr"] = "D"
    return atualizar_lancamento(banco=banco, laba_ctrl=laba_ctrl, dados=dados)


def deletar_lancamento(*, banco: str, laba_ctrl: int) -> None:
    obj = Lctobancario.objects.using(banco).filter(laba_ctrl=int(laba_ctrl)).first()
    if not obj:
        raise ValidationError({"detail": ["Lançamento não encontrado."]})
    with transaction.atomic(using=banco):
        obj.delete(using=banco)


def deletar_entrada(*, banco: str, laba_ctrl: int) -> None:
    obj = Lctobancario.objects.using(banco).filter(laba_ctrl=int(laba_ctrl)).first()
    if not obj:
        raise ValidationError({"detail": ["Lançamento não encontrado."]})
    if (obj.laba_dbcr or "").upper() != "C":
        raise ValidationError({"detail": ["Lançamento não é do tipo entrada."]})
    deletar_lancamento(banco=banco, laba_ctrl=laba_ctrl)


def deletar_saida(*, banco: str, laba_ctrl: int) -> None:
    obj = Lctobancario.objects.using(banco).filter(laba_ctrl=int(laba_ctrl)).first()
    if not obj:
        raise ValidationError({"detail": ["Lançamento não encontrado."]})
    if (obj.laba_dbcr or "").upper() != "D":
        raise ValidationError({"detail": ["Lançamento não é do tipo saída."]})
    deletar_lancamento(banco=banco, laba_ctrl=laba_ctrl)


def obter_resumo_dashboard(
    *,
    banco: str,
    empresa_id: Optional[int] = None,
    filial_id: Optional[int] = None,
    entidade_id: Optional[int] = None,
    centro_custo_id: Optional[int] = None,
    data_inicial: Optional[date] = None,
    data_final: Optional[date] = None,
    limite: int = 10,
) -> Dict[str, Any]:
    qs = Lctobancario.objects.using(banco).all()

    if empresa_id is not None:
        qs = qs.filter(laba_empr=int(empresa_id))
    if filial_id is not None:
        qs = qs.filter(laba_fili=int(filial_id))
    if entidade_id is not None:
        qs = qs.filter(Q(laba_enti=int(entidade_id)) | Q(laba_banc=int(entidade_id)))
    if centro_custo_id is not None:
        qs = qs.filter(laba_cecu=int(centro_custo_id))
    if data_inicial is not None:
        qs = qs.filter(laba_data__gte=data_inicial)
    if data_final is not None:
        qs = qs.filter(laba_data__lte=data_final)

    entradas_valor = qs.filter(laba_dbcr="C").aggregate(total=Coalesce(Sum("laba_valo"), Decimal("0.00")))[
        "total"
    ]
    saidas_valor = qs.filter(laba_dbcr="D").aggregate(total=Coalesce(Sum("laba_valo"), Decimal("0.00")))[
        "total"
    ]
    saldo_atual = (entradas_valor or Decimal("0.00")) - (saidas_valor or Decimal("0.00"))

    entradas_por_entidade = (
        qs.filter(laba_dbcr="C")
        .values("laba_enti")
        .annotate(total=Coalesce(Sum("laba_valo"), Decimal("0.00")))
        .order_by("-total")[: int(limite)]
    )
    saidas_por_entidade = (
        qs.filter(laba_dbcr="D")
        .values("laba_enti")
        .annotate(total=Coalesce(Sum("laba_valo"), Decimal("0.00")))
        .order_by("-total")[: int(limite)]
    )
    saldo_por_entidade = (
        qs.values("laba_enti")
        .annotate(
            entradas=Coalesce(Sum("laba_valo", filter=Q(laba_dbcr="C")), Decimal("0.00")),
            saidas=Coalesce(Sum("laba_valo", filter=Q(laba_dbcr="D")), Decimal("0.00")),
        )
        .annotate(saldo=F("entradas") - F("saidas"))
        .order_by("-saldo")[: int(limite)]
    )

    entradas_por_banco = (
        qs.filter(laba_dbcr="C")
        .values("laba_banc")
        .annotate(total=Coalesce(Sum("laba_valo"), Decimal("0.00")))
        .order_by("-total")[: int(limite)]
    )
    saidas_por_banco = (
        qs.filter(laba_dbcr="D")
        .values("laba_banc")
        .annotate(total=Coalesce(Sum("laba_valo"), Decimal("0.00")))
        .order_by("-total")[: int(limite)]
    )
    saldo_por_banco = (
        qs.values("laba_banc")
        .annotate(
            entradas=Coalesce(Sum("laba_valo", filter=Q(laba_dbcr="C")), Decimal("0.00")),
            saidas=Coalesce(Sum("laba_valo", filter=Q(laba_dbcr="D")), Decimal("0.00")),
        )
        .annotate(saldo=F("entradas") - F("saidas"))
        .order_by("-saldo")[: int(limite)]
    )

    entradas_por_centro_custo = (
        qs.filter(laba_dbcr="C")
        .values("laba_cecu")
        .annotate(total=Coalesce(Sum("laba_valo"), Decimal("0.00")))
        .order_by("-total")[: int(limite)]
    )
    saidas_por_centro_custo = (
        qs.filter(laba_dbcr="D")
        .values("laba_cecu")
        .annotate(total=Coalesce(Sum("laba_valo"), Decimal("0.00")))
        .order_by("-total")[: int(limite)]
    )
    saldo_por_centro_custo = (
        qs.values("laba_cecu")
        .annotate(
            entradas=Coalesce(Sum("laba_valo", filter=Q(laba_dbcr="C")), Decimal("0.00")),
            saidas=Coalesce(Sum("laba_valo", filter=Q(laba_dbcr="D")), Decimal("0.00")),
        )
        .annotate(saldo=F("entradas") - F("saidas"))
        .order_by("-saldo")[: int(limite)]
    )

    return {
        "total_lancamentos": qs.count(),
        "total_entradas": qs.filter(laba_dbcr="C").count(),
        "total_saidas": qs.filter(laba_dbcr="D").count(),
        "entradas_valor": entradas_valor or Decimal("0.00"),
        "saidas_valor": saidas_valor or Decimal("0.00"),
        "saldo_atual": saldo_atual,
        "entradas_por_entidade": list(entradas_por_entidade),
        "saidas_por_entidade": list(saidas_por_entidade),
        "saldo_por_entidade": list(saldo_por_entidade),
        "entradas_por_banco": list(entradas_por_banco),
        "saidas_por_banco": list(saidas_por_banco),
        "saldo_por_banco": list(saldo_por_banco),
        "entradas_por_centro_custo": list(entradas_por_centro_custo),
        "saidas_por_centro_custo": list(saidas_por_centro_custo),
        "saldo_por_centro_custo": list(saldo_por_centro_custo),
    }
