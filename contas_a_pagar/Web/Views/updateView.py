from django.views.generic import UpdateView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..mixin import DBAndSlugMixin
from ..forms import TitulosPagarForm
from ...models import Titulospagar


class TitulosPagarUpdateView(DBAndSlugMixin, UpdateView):
    model = Titulospagar
    form_class = TitulosPagarForm
    template_name = 'ContasAPagar/titulo_pagar_editar.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        qs = Titulospagar.objects.using(banco).all()
        emp = self.request.session.get('empresa_id')
        fil = self.request.session.get('filial_id')
        if emp:
            qs = qs.filter(titu_empr=int(emp))
        if fil:
            qs = qs.filter(titu_fili=int(fil))
        return qs

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.get_object()
        dados = form.cleaned_data
        from ...services import atualizar_titulo_pagar
        atualizar_titulo_pagar(obj, banco=banco, dados=dados)
        return redirect('contas_a_pagar_web:titulos_pagar_list', slug=self.slug)

    def get_object(self, queryset=None):
        banco = get_licenca_db_config(self.request) or 'default'
        emp = self.request.session.get('empresa_id')
        fil = self.request.session.get('filial_id')
        titu = self.kwargs.get('titu_titu')
        parcela = self.kwargs.get('titu_parc')
        qs = Titulospagar.objects.using(banco).filter(titu_titu=titu)
        if emp:
            qs = qs.filter(titu_empr=int(emp))
        if fil:
            qs = qs.filter(titu_fili=int(fil))
        if parcela:
            qs = qs.filter(titu_parc=parcela)
        obj = qs.order_by('titu_parc','titu_venc').first()
        if not obj:
            from django.http import Http404
            raise Http404('Título a pagar não encontrado')
        return obj