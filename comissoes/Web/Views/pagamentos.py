from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.utils import get_licenca_db_config
from comissoes.Web.forms import PagamentoCriarForm, PagamentoFiltroForm
from comissoes.models import LancamentoComissao, PagamentoComissao, PagamentoComissaoItem
from comissoes.services import PagamentoComissaoService
from Entidades.models import Entidades


def _contexto_base(request):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")
    if not empresa_id or not filial_id:
        raise ValueError("Selecione empresa e filial para continuar.")
    return banco, int(empresa_id), int(filial_id)


def lista(request, slug=None):
    banco, empresa_id, filial_id = _contexto_base(request)
    form = PagamentoFiltroForm(request.GET or None, request=request)

    qs = PagamentoComissao.objects.using(banco).all()
    if empresa_id:
        qs = qs.filter(pagc_empr=empresa_id)
    if filial_id:
        qs = qs.filter(pagc_fili=filial_id)

    if form.is_valid():
        bene_id = form.beneficiario_id()
        if bene_id:
            qs = qs.filter(pagc_bene=bene_id)

        cecu_id = form.centro_custo_id()
        if cecu_id is not None:
            qs = qs.filter(pagc_cecu=int(cecu_id))

        data_ini = form.cleaned_data.get("data_ini")
        if data_ini:
            qs = qs.filter(pagc_data__gte=data_ini)
        data_fim = form.cleaned_data.get("data_fim")
        if data_fim:
            qs = qs.filter(pagc_data__lte=data_fim)

        valor_min = form.cleaned_data.get("valor_min")
        if valor_min is not None:
            qs = qs.filter(pagc_valo__gte=valor_min)
        valor_max = form.cleaned_data.get("valor_max")
        if valor_max is not None:
            qs = qs.filter(pagc_valo__lte=valor_max)

    qs = qs.order_by("-pagc_data", "-pagc_id")[:300]
    total = qs.aggregate(total=Sum("pagc_valo")).get("total") or Decimal("0.00")

    bene_ids = list({int(x) for x in qs.values_list("pagc_bene", flat=True) if x is not None})
    bene_map = {}
    if bene_ids:
        bene_map = {
            int(e.enti_clie): str(e.enti_nome or "")
            for e in Entidades.objects.using(banco)
            .filter(enti_empr=int(empresa_id), enti_clie__in=bene_ids)
            .only("enti_clie", "enti_nome")
        }

    cecu_ids = list(
        {int(x) for x in qs.values_list("pagc_cecu", flat=True) if x not in (None, "", 0) and str(x).isdigit()}
    )
    cecu_map = {}
    if cecu_ids:
        try:
            from CentrodeCustos.models import Centrodecustos
        except Exception:
            Centrodecustos = None
        if Centrodecustos:
            cecu_map = {
                int(cc.cecu_redu): f"{cc.cecu_redu} - {cc.cecu_nome}"
                for cc in (
                    Centrodecustos.objects.using(banco)
                    .filter(cecu_redu__in=cecu_ids)
                    .only("cecu_redu", "cecu_nome")
                )
            }

    for p in qs:
        nome = bene_map.get(int(p.pagc_bene)) if getattr(p, "pagc_bene", None) is not None else None
        if nome:
            p.beneficiario_nome = nome
            p.beneficiario_display = f"{p.pagc_bene} - {nome}"
        else:
            p.beneficiario_nome = ""
            p.beneficiario_display = str(p.pagc_bene)
        p.centro_custo_display = cecu_map.get(int(p.pagc_cecu)) if getattr(p, "pagc_cecu", None) not in (None, "", 0) else ""

    return render(
        request,
        "comissoes/pagamentos_list.html",
        {"slug": slug, "form": form, "pagamentos": qs, "total": total},
    )


@require_http_methods(["GET", "POST"])
def criar(request, slug=None):
    banco, empresa_id, filial_id = _contexto_base(request)
    service = PagamentoComissaoService(db_alias=banco, empresa_id=empresa_id, filial_id=filial_id)

    if request.method == "POST":
        form = PagamentoCriarForm(request.POST, request=request)
        if form.is_valid():
            beneficiario_id = form.beneficiario_id()
            data_pagamento = form.cleaned_data["data"]
            observacao = form.cleaned_data.get("observacao")
            centro_custo_id = form.centro_custo_id()

            lancamento_ids = [int(x) for x in request.POST.getlist("lancamento_ids") if str(x).isdigit()]
            itens = []
            for lanc_id in lancamento_ids:
                valor_raw = request.POST.get(f"valor_{lanc_id}")
                if valor_raw is None or str(valor_raw).strip() == "":
                    itens.append({"lancamento_id": lanc_id})
                else:
                    itens.append({"lancamento_id": lanc_id, "valor": valor_raw})

            try:
                pagamento = service.gerar_pagamento(
                    beneficiario_id=beneficiario_id,
                    data_pagamento=data_pagamento,
                    itens=itens,
                    observacao=observacao,
                    centro_custo_id=centro_custo_id,
                )
                messages.success(request, "Pagamento gerado com sucesso.")
                return redirect("comissoes_web:pagamentos_detail", slug=slug, pagamento_id=pagamento.pagc_id)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = PagamentoCriarForm(request.GET or None, initial={"data": date.today()}, request=request)

    beneficiario_id = None
    lancamentos = []
    totais_pago = {}
    if form.is_valid():
        try:
            beneficiario_id = form.beneficiario_id()
        except Exception:
            beneficiario_id = None

    if beneficiario_id:
        qs = service.comissoes_em_aberto(beneficiario_id=beneficiario_id)
        lancamentos = list(qs)
        totais_pago = {
            int(x["pgci_lanc_id"]): x["total"] or Decimal("0.00")
            for x in (
                PagamentoComissaoItem.objects.using(banco)
                .filter(pgci_lanc_id__in=[l.lcom_id for l in lancamentos])
                .values("pgci_lanc_id")
                .annotate(total=Sum("pgci_valo"))
            )
        }

    itens_view = []
    total_saldo = Decimal("0.00")
    for l in lancamentos:
        pago = totais_pago.get(int(l.lcom_id)) or Decimal("0.00")
        saldo = (Decimal(str(l.lcom_valo)) - Decimal(str(pago)))
        if saldo < Decimal("0.00"):
            saldo = Decimal("0.00")
        total_saldo += saldo
        itens_view.append({"lanc": l, "pago": pago, "saldo": saldo})

    return render(
        request,
        "comissoes/pagamentos_form.html",
        {"slug": slug, "form": form, "itens": itens_view, "total_saldo": total_saldo},
    )


def detalhe(request, slug=None, pagamento_id=None):
    banco, empresa_id, filial_id = _contexto_base(request)
    pagamento = get_object_or_404(
        PagamentoComissao.objects.using(banco),
        pagc_id=int(pagamento_id),
        pagc_empr=empresa_id,
        pagc_fili=filial_id,
    )
    itens = (
        PagamentoComissaoItem.objects.using(banco)
        .filter(pgci_paga_id=pagamento.pagc_id)
        .select_related("pgci_lanc")
        .order_by("pgci_id")
    )

    bene_nome = (
        Entidades.objects.using(banco)
        .filter(enti_empr=int(empresa_id), enti_clie=int(pagamento.pagc_bene))
        .only("enti_nome")
        .values_list("enti_nome", flat=True)
        .first()
    ) or ""
    pagamento.beneficiario_nome = str(bene_nome or "")
    pagamento.beneficiario_display = (
        f"{pagamento.pagc_bene} - {pagamento.beneficiario_nome}" if pagamento.beneficiario_nome else str(pagamento.pagc_bene)
    )
    pagamento.centro_custo_display = ""
    if getattr(pagamento, "pagc_cecu", None) not in (None, "", 0):
        try:
            from CentrodeCustos.models import Centrodecustos
        except Exception:
            Centrodecustos = None
        if Centrodecustos:
            cc = (
                Centrodecustos.objects.using(banco)
                .filter(cecu_redu=int(pagamento.pagc_cecu))
                .only("cecu_redu", "cecu_nome")
                .first()
            )
            if cc:
                pagamento.centro_custo_display = f"{cc.cecu_redu} - {cc.cecu_nome}"

    return render(
        request,
        "comissoes/pagamentos_detail.html",
        {"slug": slug, "pagamento": pagamento, "itens": itens},
    )
