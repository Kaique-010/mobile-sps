from django.views.generic import CreateView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..forms import AdiantamentosForm
from ...models import Adiantamentos


class AdiantamentosCreateView(CreateView):
    model = Adiantamentos
    form_class = AdiantamentosForm
    template_name = 'Adiantamentos/adiantamento_criar.html'

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data

        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial')

        if empresa is not None:
            try:
                dados['adia_empr'] = int(empresa)
            except Exception:
                dados['adia_empr'] = empresa

        if filial is not None:
            try:
                dados['adia_fili'] = int(filial)
            except Exception:
                dados['adia_fili'] = filial

        from ...services import AdiantamentosService

        self.object = AdiantamentosService.criar_adiantamento(
            dados=dados,
            using=banco,
        )

        slug = self.kwargs.get('slug')
        return redirect('adiantamentos_web:adiantamentos_list', slug=slug)

