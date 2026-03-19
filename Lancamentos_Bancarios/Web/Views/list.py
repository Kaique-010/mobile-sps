from django.views.generic import ListView

from core.utils import get_licenca_db_config

from Lancamentos_Bancarios.models import Lctobancario
from Entidades.models import Entidades


class LancamentosListView(ListView):
    template_name = "Lancamentos_Bancarios/Lancamentos.html"
    context_object_name = "lancamentos"
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        qs = Lctobancario.objects.using(banco).all().order_by("-laba_data", "-laba_ctrl")

        empresa = self.request.GET.get("empr")
        filial = self.request.GET.get("fili")
        tipo = self.request.GET.get("tipo")

        if empresa:
            try:
                qs = qs.filter(laba_empr=int(empresa))
            except Exception:
                pass
        if filial:
            try:
                qs = qs.filter(laba_fili=int(filial))
            except Exception:
                pass
        if tipo in ("C", "D"):
            qs = qs.filter(laba_dbcr=tipo)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")

        empr = self.request.GET.get("empr") or ""
        fili = self.request.GET.get("fili") or ""
        tipo = self.request.GET.get("tipo") or ""

        ctx["filtros"] = {
            "empr": empr,
            "fili": fili,
            "tipo": tipo,
        }

        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = None
        try:
            empresa_id = int(empr) if empr else None
        except Exception:
            empresa_id = None
        if empresa_id is None:
            try:
                empresa_id = int(self.request.session.get("empresa_id")) if self.request.session.get("empresa_id") else None
            except Exception:
                empresa_id = None

        if empresa_id is not None:
            lancamentos = list(ctx.get("lancamentos") or [])
            banco_ids = {int(l.laba_banc) for l in lancamentos if getattr(l, "laba_banc", None) not in (None, "")}
            entidade_ids = {int(l.laba_enti) for l in lancamentos if getattr(l, "laba_enti", None) not in (None, "")}

            nomes_por_id = {}
            ids = banco_ids | entidade_ids
            if ids:
                qs = Entidades.objects.using(banco).filter(enti_empr=str(empresa_id), enti_clie__in=list(ids))
                nomes_por_id = {int(obj.enti_clie): obj.enti_nome for obj in qs}

            for lcto in lancamentos:
                banc_id = getattr(lcto, "laba_banc", None)
                enti_id = getattr(lcto, "laba_enti", None)
                nome_banco = nomes_por_id.get(int(banc_id)) if banc_id not in (None, "") else None
                nome_entidade = nomes_por_id.get(int(enti_id)) if enti_id not in (None, "") else None
                lcto.nome_banco = nome_banco or "-"
                lcto.nome_entidade = nome_entidade or "-"

        return ctx
