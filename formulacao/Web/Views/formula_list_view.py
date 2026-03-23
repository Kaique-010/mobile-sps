from django.views.generic import ListView
from django.db.models import Q
from django.http import JsonResponse

from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config

from Produtos.models import Produtos
from ...models import FormulaProduto


class FormulaListView(ListView):
    model = FormulaProduto
    template_name = "formulacao/formula_list.html"
    context_object_name = "formulas"
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = self.request.session.get("empresa_id", 1)
        filial_id = self.request.session.get("filial_id", 1)
        q = (self.request.GET.get("q") or "").strip()

        qs = (
            FormulaProduto.objects.using(banco)
            .select_related("form_prod")
            .filter(form_empr=int(empresa_id), form_fili=int(filial_id))
        )
        if q:
            qs = qs.filter(Q(form_prod__prod_nome__icontains=q) | Q(form_prod__prod_codi__icontains=q))
        return qs.order_by("form_prod__prod_nome", "-form_vers")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug") or get_licenca_slug()
        context["q"] = (self.request.GET.get("q") or "").strip()
        return context


def autocomplete_produtos(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id", 1)
    term = (request.GET.get("term") or request.GET.get("q") or "").strip()

    qs = Produtos.objects.using(banco).filter(prod_empr=str(empresa_id))
    if term:
        if term.isdigit():
            qs = qs.filter(prod_codi__icontains=term)
        else:
            qs = qs.filter(prod_nome__icontains=term)
    qs = qs.order_by("prod_nome")[:20]
    data = [{"id": str(obj.prod_codi), "text": f"{obj.prod_codi} - {obj.prod_nome}"} for obj in qs]
    return JsonResponse({"results": data})
