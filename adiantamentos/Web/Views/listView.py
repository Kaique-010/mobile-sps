from django.views.generic import ListView
from core.utils import get_licenca_db_config
from ..forms import AdiantamentosForm
from ...models import Adiantamentos
from Entidades.models import Entidades


class AdiantamentosListView(ListView):
    model = Adiantamentos
    template_name = 'Adiantamentos/adiantamentos_list.html'
    context_object_name = 'adiantamentos'
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        qs = Adiantamentos.objects.using(banco).all()

        tipo = self.request.GET.get('adia_tipo')
        entidade = self.request.GET.get('adia_enti')

        if tipo:
            qs = qs.filter(adia_tipo=tipo)
        if entidade:
            qs = qs.filter(adia_enti=entidade)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('form_filtro', AdiantamentosForm())
        context['slug'] = self.kwargs.get('slug')

        banco = get_licenca_db_config(self.request) or 'default'
        objs = list(context.get('adiantamentos') or [])
        ids = {o.adia_enti for o in objs if getattr(o, 'adia_enti', None) is not None}
        nomes_map = {}
        if ids:
            ents = Entidades.objects.using(banco).filter(enti_clie__in=ids)
            for e in ents:
                try:
                    key = int(e.enti_clie)
                except Exception:
                    key = e.enti_clie
                nomes_map[key] = e.enti_nome
        for o in objs:
            try:
                key = int(o.adia_enti)
            except Exception:
                key = o.adia_enti
            setattr(o, 'entidade_nome', nomes_map.get(key, ''))
        return context
