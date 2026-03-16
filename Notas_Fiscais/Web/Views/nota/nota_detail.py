# notas_fiscais/views/nota/nota_detail.py

from django.views.generic import DetailView
from core.utils import get_licenca_db_config
from ....models import Nota
from Licencas.models import Filiais
from Entidades.models import Entidades
from decimal import Decimal



class NotaDetailView(DetailView):
    model = Nota
    template_name = "notas/nota_detail.html"
    context_object_name = "nota"

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        filial = self.request.session.get("filial_id")
        qs = Nota.objects.using(banco).prefetch_related("itens__impostos")
        if empresa is not None:
            qs = qs.filter(empresa=empresa)
        if filial is not None:
            qs = qs.filter(filial=filial)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or "default"
        nota: Nota = ctx.get("nota")
        nota_referencia = nota.chave_referenciada or ""
        emitente = Filiais.objects.using(banco).defer('empr_cert_digi').get(empr_empr=nota.empresa, empr_codi=nota.filial)
        destinatario = Entidades.objects.using(banco).get(enti_empr=nota.empresa, enti_clie=nota.destinatario_id)
        itens = list(getattr(nota, "itens", []).all())
        total_produtos = sum(((it.total or Decimal("0"))) for it in itens)
        total_descontos = sum(((it.desconto or Decimal("0"))) for it in itens)
        total_tributos = Decimal("0")
        for it in itens:
            imp = getattr(it, "impostos", None)
            if not imp:
                continue
            total_tributos += (
                (imp.icms_valor or Decimal("0"))
                + (imp.icms_st_valor or Decimal("0"))
                + (imp.ipi_valor or Decimal("0"))
                + (imp.pis_valor or Decimal("0"))
                + (imp.cofins_valor or Decimal("0"))
                + (imp.cbs_valor or Decimal("0"))
                + (imp.ibs_valor or Decimal("0"))
                + (imp.fcp_valor or Decimal("0"))
            )
        ctx["total_tributos"] = total_tributos
        ctx["total_descontos"] = total_descontos
        ctx["total_nota"] = total_produtos + total_tributos
        ctx["emitente"] = emitente
        ctx["destinatario"] = destinatario
        ctx["slug"] = self.kwargs.get("slug")
        ctx["nota_referencia"] = nota_referencia
        return ctx
