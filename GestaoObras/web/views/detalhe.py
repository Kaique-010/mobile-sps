from django.shortcuts import render, get_object_or_404
from datetime import date
from decimal import Decimal
from django.db.models import Sum, Count
from django.db.utils import ProgrammingError, OperationalError
from core.utils import get_licenca_db_config
from GestaoObras.models import Obra, ObraEtapa, ObraMaterialMovimento, ObraLancamentoFinanceiro, ObraProcesso, ObraMaterialEstoqueSaldo


def detalhe_obra(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    active_tab = (request.GET.get("tab") or "detalhes").strip().lower()
    open_sec = (request.GET.get("sec") or "etapas").strip().lower()
    etapas = ObraEtapa.objects.using(banco).filter(etap_obra_id=obra.id).order_by("etap_orde", "id")
    movimentos = (
        ObraMaterialMovimento.objects.using(banco)
        .filter(movm_obra_id=obra.id)
        .order_by("-movm_data", "-movm_codi")[:20]
    )
    estoque_movimentos = []
    try:
        estoque_movimentos = list(
            ObraMaterialEstoqueSaldo.objects.using(banco)
            .filter(omes_obra_id=obra.id)
            .order_by("-omes_data_movi", "-id")[:20]
        )
    except (ProgrammingError, OperationalError):
        estoque_movimentos = []

    dash_total_investimento = obra.obra_orca or Decimal("0")
    fin_qs_all = ObraLancamentoFinanceiro.objects.using(banco).filter(lfin_obra_id=obra.id)
    dash_total_despesa = (
        fin_qs_all.filter(lfin_tipo="DE").aggregate(total=Sum("lfin_valo"))["total"] or Decimal("0")
    )
    dash_total_receita = (
        fin_qs_all.filter(lfin_tipo="RE").aggregate(total=Sum("lfin_valo"))["total"] or Decimal("0")
    )
    dash_saldo = dash_total_investimento - dash_total_despesa
    dash_percentual_usado = None
    if dash_total_investimento and dash_total_investimento > 0:
        dash_percentual_usado = (dash_total_despesa / dash_total_investimento) * 100

    dash_etapa_maior_gasto = (
        fin_qs_all.filter(lfin_tipo="DE", lfin_etap__isnull=False)
        .values("lfin_etap__etap_codi", "lfin_etap__etap_nome")
        .annotate(total=Sum("lfin_valo"))
        .order_by("-total")
        .first()
    )

    dash_etapas_total = ObraEtapa.objects.using(banco).filter(etap_obra_id=obra.id).count()
    dash_processos_total = ObraProcesso.objects.using(banco).filter(proc_obra_id=obra.id).count()
    dash_processos_abertos = (
        ObraProcesso.objects.using(banco).filter(proc_obra_id=obra.id).exclude(proc_stat="CO").count()
    )
    dash_movimentos_total = ObraMaterialMovimento.objects.using(banco).filter(movm_obra_id=obra.id).count()
    dash_movimentos_por_tipo = list(
        ObraMaterialMovimento.objects.using(banco)
        .filter(movm_obra_id=obra.id)
        .values("movm_tipo")
        .annotate(total=Count("id"))
        .order_by("movm_tipo")
    )
    fin_status = (request.GET.get("fin_status") or "").strip().upper()
    fin_dini_raw = (request.GET.get("fin_dini") or "").strip()
    fin_dfim_raw = (request.GET.get("fin_dfim") or "").strip()
    fin_dini = None
    fin_dfim = None
    try:
        if fin_dini_raw:
            fin_dini = date.fromisoformat(fin_dini_raw)
    except Exception:
        fin_dini = None
    try:
        if fin_dfim_raw:
            fin_dfim = date.fromisoformat(fin_dfim_raw)
    except Exception:
        fin_dfim = None

    lanc_qs = ObraLancamentoFinanceiro.objects.using(banco).filter(lfin_obra_id=obra.id)
    if fin_status == "AB":
        lanc_qs = lanc_qs.filter(lfin_dpag__isnull=True)
    elif fin_status == "PG":
        lanc_qs = lanc_qs.filter(lfin_dpag__isnull=False)
    if fin_dini:
        lanc_qs = lanc_qs.filter(lfin_dcom__gte=fin_dini)
    if fin_dfim:
        lanc_qs = lanc_qs.filter(lfin_dcom__lte=fin_dfim)
    lancamentos = lanc_qs.order_by("-lfin_dcom", "-lfin_codi")[:20]
    processos = ObraProcesso.objects.using(banco).filter(proc_obra_id=obra.id).order_by("-proc_codi")[:20]
    return render(
        request,
        "obras/detalhe.html",
        {
            "slug": slug,
            "obra": obra,
            "active_tab": active_tab,
            "open_sec": open_sec,
            "etapas": etapas,
            "movimentos": movimentos,
            "estoque_movimentos": estoque_movimentos,
            "lancamentos": lancamentos,
            "processos": processos,
            "fin_status": fin_status,
            "fin_dini": fin_dini_raw,
            "fin_dfim": fin_dfim_raw,
            "dash_total_investimento": dash_total_investimento,
            "dash_total_despesa": dash_total_despesa,
            "dash_total_receita": dash_total_receita,
            "dash_saldo": dash_saldo,
            "dash_percentual_usado": dash_percentual_usado,
            "dash_etapa_maior_gasto": dash_etapa_maior_gasto,
            "dash_etapas_total": dash_etapas_total,
            "dash_processos_total": dash_processos_total,
            "dash_processos_abertos": dash_processos_abertos,
            "dash_movimentos_total": dash_movimentos_total,
            "dash_movimentos_por_tipo": dash_movimentos_por_tipo,
        },
    )
