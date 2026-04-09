from django.shortcuts import redirect
from django.views.generic import UpdateView

from core.utils import get_licenca_db_config
from TrocasDevolucoes.Web.forms import TrocaDevolucaoForm
from TrocasDevolucoes.models import TrocaDevolucao
from TrocasDevolucoes.services.troca_devolucao_service import TrocaDevolucaoService


class DevolucaoUpdateView(UpdateView):
    form_class = TrocaDevolucaoForm
    template_name = 'TrocasDevolucoes/devolucao_form.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return TrocaDevolucao.objects.using(banco).all()

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request)
        self.object = TrocaDevolucaoService.atualizar(
            banco,
            self.object,
            {k: v for k, v in form.cleaned_data.items()},
        )
        return redirect('TrocasDevolucoesWeb:devolucoes_listar', slug=self.kwargs.get('slug'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        context['titulo'] = f'Editar Devolução #{self.object.tdvl_nume}'
        return context
