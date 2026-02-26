from django.views.generic import CreateView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..forms import BensptrForm
from ...models import Bensptr
from ...Web.Services.registrar_bens import BensptrService

class BensCreateView(CreateView):
    model = Bensptr
    form_class = BensptrForm
    template_name = 'Bens/bens_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')
        if empresa:
            kwargs['empresa'] = int(empresa)
        if filial:
            kwargs['filial'] = int(filial)
        return kwargs

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')

        if empresa:
            dados['bens_empr'] = int(empresa)
        if filial:
            dados['bens_fili'] = int(filial)
            
        # Converter objetos relacionados para IDs se o Service esperar IDs
        # O Service BensptrService.criar_bem espera 'bens_grup' como ID (pois Bensptr.bens_grup é IntegerField)
        # O Form usa ModelChoiceField, então 'bens_grup' no cleaned_data é um objeto Grupobens.
        if dados.get('bens_grup'):
            dados['bens_grup'] = dados['bens_grup'].grup_codi
            
        if dados.get('bens_moti'):
            dados['bens_moti'] = dados['bens_moti'].moti_codi
            
        if dados.get('bens_forn'):
            # bens_forn é IntegerField? Vamos assumir que sim, Entidades.enti_clie (que é PK)
            # Mas Entidades PK é BigIntegerField.
            dados['bens_forn'] = dados['bens_forn'].enti_clie

        self.object = BensptrService.criar_bem(
            dados=dados,
            using=banco,
        )

        slug = self.kwargs.get('slug')
        # Redirecionar para lista
        # Precisamos definir o namespace 'bens_web' no urls.py
        return redirect('bens_web:bens_list', slug=slug)
