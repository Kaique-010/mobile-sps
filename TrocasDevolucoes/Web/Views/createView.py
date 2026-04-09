from django.shortcuts import redirect
from django.views.generic import CreateView

from core.utils import get_licenca_db_config
from TrocasDevolucoes.Web.forms import TrocaDevolucaoForm
from TrocasDevolucoes.services.troca_devolucao_service import TrocaDevolucaoService


class DevolucaoCreateView(CreateView):
    form_class = TrocaDevolucaoForm
    template_name = 'TrocasDevolucoes/devolucao_form.html'

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request)
        dados = form.cleaned_data
        self.object = TrocaDevolucaoService.criar_com_itens(banco, dados=dados, itens=[])
        return redirect('TrocasDevolucoesWeb:devolucoes_listar', slug=self.kwargs.get('slug'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        context['titulo'] = 'Nova Devolução'
        return context
