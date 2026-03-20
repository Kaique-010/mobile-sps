from django.views.generic import TemplateView
from datetime import date

from ....models import FINALIDADE_CHOICES, MODALIDADE_FRETE
from core.utils import get_licenca_db_config
from series.models import Series
from Licencas.models import Filiais


def _to_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default


def _fmt_serie(v):
    s = str(v or "").strip()
    if s.isdigit() and len(s) < 3:
        return s.zfill(3)
    return s


class NotaEmissaoView(TemplateView):
    template_name = "notas/nota_emissao.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")

        banco = get_licenca_db_config(self.request) or "default"
        empresa = (
            self.request.session.get("empresa_id")
            or self.request.GET.get("empresa")
            or self.request.headers.get("X-Empresa")
        )
        filial = (
            self.request.session.get("filial_id")
            or self.request.GET.get("filial")
            or self.request.headers.get("X-Filial")
        )
        empresa_id = _to_int(empresa, 1)
        filial_id = _to_int(filial, 1)

        emitente = (
            Filiais.objects.using(banco)
            .filter(empr_empr=empresa_id, empr_codi=filial_id)
            .first()
        )
        try:
            regime_emitente = str(getattr(emitente, "empr_regi_trib", "") or "").strip()
        except Exception:
            regime_emitente = ""
        is_produtor_rural = regime_emitente == "5"

        if is_produtor_rural:
            serie_tipos = ["PR"]
        else:
            serie_tipos = ["SA", "NC"]

        series_qs = (
            Series.objects.using(banco)
            .filter(seri_empr=empresa_id, seri_fili=filial_id, seri_nome__in=serie_tipos)
            .order_by("seri_codi")
            .values_list("seri_codi", flat=True)
        )
        if is_produtor_rural:
            series_qs = series_qs.filter(seri_codi__gte="920", seri_codi__lte="969")
        serie_opcoes = [{"value": _fmt_serie(c), "label": _fmt_serie(c)} for c in list(series_qs)]
        serie_opcoes = [o for o in serie_opcoes if o.get("value")]
        ctx["serie_opcoes"] = serie_opcoes
        ctx["serie_default"] = serie_opcoes[0]["value"] if serie_opcoes else "1"

        hoje = date.today().isoformat()
        ctx["data_emissao_default"] = hoje
        ctx["data_saida_default"] = hoje
        ctx["natureza_operacao_default"] = "Venda de mercadoria"
        ctx["natureza_operacao_opcoes"] = [
            {"value": "Venda de mercadoria", "label": "Venda de mercadoria"},
            {"value": "Venda de produção do estabelecimento", "label": "Venda de produção do estabelecimento"},
            {"value": "Devolução de venda", "label": "Devolução de venda"},
            {"value": "Remessa", "label": "Remessa"},
        ]
        ctx["tipo_documento_default"] = 1
        ctx["tipo_documento_opcoes"] = [{"value": v, "label": l} for v, l in FINALIDADE_CHOICES]
        ctx["modalidade_frete_default"] = 9
        ctx["modalidade_frete_opcoes"] = [{"value": v, "label": l} for v, l in MODALIDADE_FRETE]
        return ctx
