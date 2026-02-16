from django.views.generic import CreateView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..mixin import DBAndSlugMixin
from ..forms import TitulosPagarForm
from ...models import Titulospagar


class TitulosPagarCreateView(DBAndSlugMixin, CreateView):
    model = Titulospagar
    form_class = TitulosPagarForm
    template_name = 'ContasAPagar/titulo_pagar_criar.html'

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        empresa = (self.request.session.get('empresa_id')
               or self.request.headers.get('X-Empresa')
               or self.request.GET.get('titu_empr')
               or getattr(self, 'empresa_id', None))
        filial = (self.request.session.get('filial_id')
               or self.request.headers.get('X-Filial')
               or self.request.GET.get('titu_fili')
               or getattr(self, 'filial_id', None))
        if empresa is not None:
            try:
                dados['titu_empr'] = int(empresa)
            except Exception:
                dados['titu_empr'] = empresa
        if filial is not None:
            try:
                dados['titu_fili'] = int(filial)
            except Exception:
                dados['titu_fili'] = filial 
        from ...services import criar_titulo_pagar, gera_parcelas_a_pagar
        self.object = criar_titulo_pagar(banco=banco, dados=dados)
        gera_parcelas_a_pagar(
            titulo=self.object,
            banco=banco,
        )
        return redirect('contas_a_pagar_web:titulos_pagar_list', slug=self.slug)

class TitulosPagarParcelasCreateView(DBAndSlugMixin, CreateView):
    model = Titulospagar
    form_class = TitulosPagarForm
    template_name = 'ContasAPagar/parcelas_a_pagar.html'
    
    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        empresa = (self.request.session.get('empresa_id')
               or self.request.headers.get('X-Empresa')
               or self.request.GET.get('titu_empr')
               or getattr(self, 'empresa_id', None))
        filial = (self.request.session.get('filial_id')
               or self.request.headers.get('X-Filial')
               or self.request.GET.get('titu_fili')
               or getattr(self, 'filial_id', None))
        if empresa is not None:
            try:
                dados['titu_empr'] = int(empresa)
            except Exception:
                dados['titu_empr'] = empresa
        if filial is not None:
            try:
                dados['titu_fili'] = int(filial)
            except Exception:
                dados['titu_fili'] = filial 
        from ...services import criar_titulo_pagar, gera_parcelas_a_pagar
        self.object = criar_titulo_pagar(banco=banco, dados=dados)
        gera_parcelas_a_pagar(
            titulo=self.object,
            banco=banco,
        )
        return redirect('contas_a_pagar_web:parcelas_a_pagar_list', slug=self.slug)
