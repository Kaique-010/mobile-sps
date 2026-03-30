from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F, Sum, Case, When, Value, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from core.utils import get_licenca_db_config
from GestaoObras.web.forms import ObraLancamentoFinanceiroForm
from GestaoObras.models import Obra, ObraEtapa, ObraLancamentoFinanceiro
from GestaoObras.services.obras_service import ObrasService


def listar_financeiro(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    qs = ObraLancamentoFinanceiro.objects.using(banco).filter(lfin_obra_id=obra.id).order_by("-lfin_dcom", "-lfin_codi")
    tipo = request.GET.get("tipo")
    etapa_id = request.GET.get("etapa_id")
    mov_id = request.GET.get("mov_id")
    if tipo:
        qs = qs.filter(lfin_tipo=tipo)
    if etapa_id:
        qs = qs.filter(lfin_etap_id=etapa_id)
    if mov_id:
        qs = qs.filter(lfin_obse__icontains=f"mov_id={mov_id}")

    agg = qs.aggregate(
        total_despesa=Coalesce(
            Sum(
                Case(
                    When(lfin_tipo="DE", then=F("lfin_valo")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                )
            ),
            Value(0),
        ),
        total_receita=Coalesce(
            Sum(
                Case(
                    When(lfin_tipo="RE", then=F("lfin_valo")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                )
            ),
            Value(0),
        ),
    )

    total_investimento = getattr(obra, "obra_orca", None) or Decimal("0")
    total_despesa = agg.get("total_despesa") or Decimal("0")
    total_receita = agg.get("total_receita") or Decimal("0")
    custo_liquido = total_despesa - total_receita
    saldo = total_investimento - custo_liquido
    percentual_usado = None
    try:
        if total_investimento and Decimal(total_investimento) > 0:
            percentual_usado = (Decimal(custo_liquido) / Decimal(total_investimento)) * Decimal("100")
    except Exception:
        percentual_usado = None

    etapa_top = (
        qs.filter(lfin_tipo="DE", lfin_etap__isnull=False)
        .values("lfin_etap_id", "lfin_etap__etap_codi", "lfin_etap__etap_nome")
        .annotate(total=Sum("lfin_valo"))
        .order_by("-total")
        .first()
    )

    etapas = ObraEtapa.objects.using(banco).filter(etap_obra_id=obra.id).order_by("etap_orde", "id")
    return render(
        request,
        "obras/financeiro_listar.html",
        {
            "slug": slug,
            "obra": obra,
            "lancamentos": qs,
            "etapas": etapas,
            "tipo": tipo,
            "etapa_id": etapa_id,
            "mov_id": mov_id,
            "total_investimento": total_investimento,
            "total_despesa": total_despesa,
            "total_receita": total_receita,
            "custo_liquido": custo_liquido,
            "saldo": saldo,
            "percentual_usado": percentual_usado,
            "etapa_maior_gasto": etapa_top,
        },
    )


def criar_lancamento_financeiro(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    initial = {
        "lfin_empr": obra.obra_empr,
        "lfin_fili": obra.obra_fili,
        "lfin_obra": obra.id,
        "lfin_tipo": request.GET.get("tipo") or "DE",
        "lfin_codi": ObrasService.proximo_codigo_financeiro(banco, obra.obra_empr, obra.obra_fili),
    }
    if request.method == "POST":
        form = ObraLancamentoFinanceiroForm(request.POST, banco=banco, initial=initial)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.lfin_empr = obra.obra_empr
            obj.lfin_fili = obra.obra_fili
            obj.lfin_obra_id = obra.id
            if obj.lfin_etap_id:
                exists = ObraEtapa.objects.using(banco).filter(pk=obj.lfin_etap_id, etap_obra_id=obra.id).exists()
                if not exists:
                    obj.lfin_etap_id = None
            obj.save(using=banco)
            ObrasService.consolidar_custo_obra(obra=obra, banco=banco)
            return redirect("gestaoobras:obras_financeiro_list", slug=slug, obra_id=obra.id)
    else:
        form = ObraLancamentoFinanceiroForm(banco=banco, initial=initial)
    return render(request, "obras/financeiro_criar.html", {"slug": slug, "obra": obra, "form": form})


def editar_lancamento_financeiro(request, slug, obra_id: int, lancamento_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    lanc = get_object_or_404(ObraLancamentoFinanceiro.objects.using(banco), pk=lancamento_id, lfin_obra_id=obra.id)
    initial = {"lfin_empr": obra.obra_empr, "lfin_fili": obra.obra_fili, "lfin_obra": obra.id}

    if request.method == "POST":
        form = ObraLancamentoFinanceiroForm(request.POST, banco=banco, initial=initial, instance=lanc)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.lfin_empr = obra.obra_empr
            obj.lfin_fili = obra.obra_fili
            obj.lfin_obra_id = obra.id
            if obj.lfin_etap_id:
                exists = ObraEtapa.objects.using(banco).filter(pk=obj.lfin_etap_id, etap_obra_id=obra.id).exists()
                if not exists:
                    obj.lfin_etap_id = None
            obj.save(using=banco)
            ObrasService.consolidar_custo_obra(obra=obra, banco=banco)
            return redirect("gestaoobras:obras_detail", slug=slug, obra_id=obra.id)
    else:
        form = ObraLancamentoFinanceiroForm(banco=banco, initial=initial, instance=lanc)
    return render(request, "obras/financeiro_criar.html", {"slug": slug, "obra": obra, "form": form})
