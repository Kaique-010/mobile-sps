# financeiro/views/orcamento_views.py
from decimal import Decimal
from django.views.generic import TemplateView
from django.utils import timezone
from django.http import JsonResponse

from core.utils import get_licenca_db_config
from Financeiro.services import OrcamentoService
from Financeiro.models import Orcamento


class OrcamentoDashboardTemplateView(TemplateView):
    template_name = "Financeiro/orcamento/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = kwargs.get("slug")

        db_alias = get_licenca_db_config(self.request)
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id")

        ano = int(self.request.GET.get("ano", timezone.now().year))
        mes = int(self.request.GET.get("mes", timezone.now().month))
        expandir = str(self.request.GET.get("expandir") or "").strip() in ("1", "true", "True", "on", "yes", "sim", "SIM")
        dbcr = str(self.request.GET.get("dbcr") or "A").strip().upper()
        orcamento_id = self.request.GET.get("orcamento_id")
        centro_custo_raw = self.request.GET.get("centro_custo_id") or self.request.GET.get("centro_custo")
        centro_custo_id = None
        if centro_custo_raw:
            try:
                centro_custo_id = int(centro_custo_raw)
            except Exception:
                centro_custo_id = None
        orcamento_id_int = None
        if orcamento_id:
            try:
                orcamento_id_int = int(orcamento_id)
            except Exception:
                orcamento_id_int = None

        if orcamento_id_int is None:
            qs = Orcamento.objects.using(db_alias).filter(
                orca_empr=empresa_id,
                orca_ativ=True,
            )
            try:
                qs = qs.filter(orca_ano=ano)
            except Exception:
                pass
            if filial_id:
                qs = qs.filter(orca_fili=filial_id)
            orc = qs.order_by("-orca_id").first()
            if orc:
                orcamento_id_int = int(getattr(orc, "orca_id"))

        orcamentos_qs = Orcamento.objects.using(db_alias).filter(orca_empr=empresa_id).order_by("-orca_id")
        if filial_id:
            orcamentos_qs = orcamentos_qs.filter(orca_fili=filial_id)
        context["orcamentos"] = list(
            orcamentos_qs.values("orca_id", "orca_desc", "orca_ano", "orca_tipo", "orca_cena", "orca_ativ")[:200]
        )

        service = OrcamentoService(
            db_alias=db_alias,
            empresa_id=empresa_id,
            filial_id=filial_id,
        )

        if orcamento_id_int is None:
            context["dados"] = []
        else:
            context["dados"] = service.resumo_raiz(
                orcamento_id=orcamento_id_int,
                ano=ano,
                mes=mes,
                expandir=expandir,
                dbcr=dbcr,
                centro_custo_id=centro_custo_id,
            )

        orcado_series = []
        realizado_series = []
        if orcamento_id_int is not None:
            orcado_series = service.previsto_total_por_mes(
                orcamento_id=orcamento_id_int,
                ano=ano,
                centro_custo_id=centro_custo_id,
            )
            realizado_series = service.realizado_total_por_mes(
                ano=ano,
                dbcr=dbcr,
                centro_custo_id=centro_custo_id,
            )

        mes_idx = max(1, min(12, int(mes))) - 1
        orcado_mes = orcado_series[mes_idx] if orcado_series else Decimal("0.00")
        realizado_mes = realizado_series[mes_idx] if realizado_series else Decimal("0.00")
        saldo_mes = orcado_mes - realizado_mes
        percentual_mes = Decimal("0.00")
        if orcado_mes:
            percentual_mes = (realizado_mes / orcado_mes) * Decimal("100.00")

        context["kpis"] = {
            "orcado_mes": orcado_mes,
            "realizado_mes": realizado_mes,
            "saldo_mes": saldo_mes,
            "percentual_mes": percentual_mes.quantize(Decimal("0.01")),
        }
        context["mensal_json"] = {
            "labels": list(range(1, 13)),
            "orcado": [float(v) for v in (orcado_series or [Decimal("0.00")] * 12)],
            "realizado": [float(v) for v in (realizado_series or [Decimal("0.00")] * 12)],
        }
        context["ano"] = ano
        context["mes"] = mes
        context["orcamento_id"] = orcamento_id_int
        context["expandir"] = expandir
        context["dbcr"] = dbcr
        context["centro_custo_id"] = centro_custo_id
        if centro_custo_id:
            centro = service.obter_centro(int(centro_custo_id))
            if centro:
                context["centro_custo_display"] = f"{centro.cecu_redu} - {centro.cecu_nome}"
            else:
                context["centro_custo_display"] = ""
        else:
            context["centro_custo_display"] = ""
        return context


def orcamento_realizado_detalhe(request, slug=None):
    db_alias = get_licenca_db_config(request)
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")

    centro_custo_id = request.GET.get("centro_custo_id")
    ano = request.GET.get("ano")
    mes = request.GET.get("mes")
    dbcr = request.GET.get("dbcr") or "A"
    limite = request.GET.get("limite") or 300

    try:
        centro_custo_id_int = int(centro_custo_id)
        ano_int = int(ano)
        mes_int = int(mes)
        limite_int = int(limite)
    except Exception:
        return JsonResponse({"rows": [], "total": 0}, status=400)

    if not empresa_id:
        return JsonResponse({"rows": [], "total": 0}, status=400)

    service = OrcamentoService(
        db_alias=db_alias,
        empresa_id=int(empresa_id),
        filial_id=int(filial_id) if filial_id else None,
    )
    rows = service.detalhar_realizado(
        centro_custo_id=centro_custo_id_int,
        ano=ano_int,
        mes=mes_int,
        dbcr=dbcr,
        limite=limite_int,
    )
    total = 0
    try:
        total = sum([float(r.get("laba_valo") or 0) for r in rows])
    except Exception:
        total = 0
    return JsonResponse({"rows": rows, "total": total})
