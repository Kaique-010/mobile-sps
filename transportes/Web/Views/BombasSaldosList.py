from django.db.models import Q
from django.views.generic import ListView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import BombasSaldos
from transportes.services.bombas_saldos import BombasSaldosService


class BombasSaldosListView(ListView):
    model = BombasSaldos
    template_name = "transportes/bombas_saldos_lista.html"
    context_object_name = "movimentos"
    paginate_by = 20

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_queryset(self):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1

        qs = BombasSaldos.objects.using(banco).filter(bomb_empr=empresa_id, bomb_fili=filial_id)

        term = (self.request.GET.get("q") or "").strip()
        if term:
            qs = qs.filter(
                Q(bomb_bomb__icontains=term)
                | Q(bomb_comb__icontains=term)
                | Q(bomb_tipo_movi__icontains=term)
            )

        bomb_bomb = (self.request.GET.get("bomb_bomb") or "").strip()
        if bomb_bomb:
            qs = qs.filter(bomb_bomb=bomb_bomb)

        bomb_comb = (self.request.GET.get("bomb_comb") or "").strip()
        if bomb_comb:
            qs = qs.filter(bomb_comb=bomb_comb)

        return qs.order_by("-bomb_data", "-bomb_id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug")
        banco = self._get_banco()
        empresa_id = int(self.request.session.get("empresa_id") or 0)
        filial_id = int(self.request.session.get("filial_id") or 1)

        context["titulo"] = "Movimentação de Combustível por Bomba"
        qs = self.get_queryset()
        context["total_movimentos"] = qs.count()

        bomb_bomb = (self.request.GET.get("bomb_bomb") or "").strip()
        bomb_comb = (self.request.GET.get("bomb_comb") or "").strip()
        context["saldo_atual"] = None
        if bomb_bomb and not bomb_comb:
            combs = (
                qs.exclude(bomb_comb__isnull=True)
                .exclude(bomb_comb="")
                .values_list("bomb_comb", flat=True)
                .distinct()
            )
            if combs.count() == 1:
                bomb_comb = combs.first() or ""

        if bomb_bomb and bomb_comb and empresa_id:
            context["saldo_atual"] = BombasSaldosService.calcular_saldo_atual(
                using=banco,
                empresa_id=empresa_id,
                filial_id=filial_id,
                bomb_bomb=bomb_bomb,
                bomb_comb=bomb_comb,
            )
        return context

