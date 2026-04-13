from decimal import Decimal

from django.db.models import Q, Sum
from django.shortcuts import render

from core.utils import get_licenca_db_config
from comissoes.Web.forms import LancamentoFiltroForm
from comissoes.models import LancamentoComissao
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
    form = LancamentoFiltroForm(request.GET or None, request=request)

    qs = LancamentoComissao.objects.using(banco).all()
    if empresa_id:
        qs = qs.filter(lcom_empr=empresa_id)
    if filial_id:
        qs = qs.filter(lcom_fili=filial_id)

    if form.is_valid():
        bene_id = form.beneficiario_id()
        if bene_id:
            qs = qs.filter(lcom_bene=bene_id)

        cecu_id = form.centro_custo_id()
        if cecu_id is not None:
            qs = qs.filter(lcom_cecu=int(cecu_id))

        tipo_origem = str(form.cleaned_data.get("tipo_origem") or "").strip()
        if tipo_origem:
            qs = qs.filter(lcom_tipo_origem=tipo_origem)

        status_param = str(form.cleaned_data.get("status") or "").strip()
        if status_param.isdigit():
            qs = qs.filter(lcom_stat=int(status_param))

        documento = str(form.cleaned_data.get("documento") or "").strip()
        if documento:
            qs = qs.filter(Q(lcom_docu__icontains=documento))

        data_ini = form.cleaned_data.get("data_ini")
        if data_ini:
            qs = qs.filter(lcom_data__gte=data_ini)
        data_fim = form.cleaned_data.get("data_fim")
        if data_fim:
            qs = qs.filter(lcom_data__lte=data_fim)

        valor_min = form.cleaned_data.get("valor_min")
        if valor_min is not None:
            qs = qs.filter(lcom_valo__gte=valor_min)
        valor_max = form.cleaned_data.get("valor_max")
        if valor_max is not None:
            qs = qs.filter(lcom_valo__lte=valor_max)

    qs = qs.order_by("-lcom_data", "-lcom_id")[:500]

    from comissoes.models import PagamentoComissaoItem
    
    totais = qs.aggregate(total_base=Sum("lcom_base"), total_valor=Sum("lcom_valo"))
    total_base = totais.get("total_base") or Decimal("0.00")
    total_valor = totais.get("total_valor") or Decimal("0.00")

    bene_ids = list({int(x) for x in qs.values_list("lcom_bene", flat=True) if x is not None})
    bene_map = {}
    if bene_ids:
        bene_map = {
            int(e.enti_clie): str(e.enti_nome or "")
            for e in Entidades.objects.using(banco)
            .filter(enti_empr=int(empresa_id), enti_clie__in=bene_ids)
            .only("enti_clie", "enti_nome")
        }
    cecu_ids = list(
        {int(x) for x in qs.values_list("lcom_cecu", flat=True) if x not in (None, "", 0) and str(x).isdigit()}
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
            
    lanc_ids = [l.lcom_id for l in qs]
    totais_pago = {}
    if lanc_ids:
        totais_pago = {
            int(x["pgci_lanc_id"]): x["total"] or Decimal("0.00")
            for x in (
                PagamentoComissaoItem.objects.using(banco)
                .filter(pgci_lanc_id__in=lanc_ids)
                .values("pgci_lanc_id")
                .annotate(total=Sum("pgci_valo"))
            )
        }

    for l in qs:
        nome = bene_map.get(int(l.lcom_bene)) if getattr(l, "lcom_bene", None) is not None else None
        if nome:
            l.beneficiario_nome = nome
            l.beneficiario_display = f"{l.lcom_bene} - {nome}"
        else:
            l.beneficiario_nome = ""
            l.beneficiario_display = str(l.lcom_bene)
        l.centro_custo_display = cecu_map.get(int(l.lcom_cecu)) if getattr(l, "lcom_cecu", None) not in (None, "", 0) else ""
        
        # Adiciona atributo ja_pago
        l.ja_pago = totais_pago.get(int(l.lcom_id)) or Decimal("0.00")

    return render(
        request,
        "comissoes/lancamentos_list.html",
        {
            "slug": slug,
            "form": form,
            "lancamentos": qs,
            "total_base": total_base,
            "total_valor": total_valor,
        },
    )
