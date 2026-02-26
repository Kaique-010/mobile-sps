from django.views.generic import UpdateView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..forms import BensptrForm
from ...models import Bensptr
from ...Web.Services.registrar_bens import BensptrService

class BensUpdateView(UpdateView):
    model = Bensptr
    form_class = BensptrForm
    template_name = 'Bens/bens_form.html'

    def get_object(self, queryset=None):
        # Implementar busca personalizada se a URL passar parâmetros diferentes
        # O UpdateView padrão espera 'pk' ou 'slug'.
        # Nossa PK é composta? Não, bens_empr é PK.
        # Mas Bensptr tem 'unique_together = (('bens_empr', 'bens_fili', 'bens_codi'),)'
        # PK é bens_empr, mas isso não é único globalmente.
        # Precisamos buscar pelo conjunto.
        # URL pattern deve passar empresa/filial/codigo.
        
        empresa = self.kwargs.get('bens_empr')
        filial = self.kwargs.get('bens_fili')
        codigo = self.kwargs.get('bens_codi')
        
        banco = get_licenca_db_config(self.request) or 'default'
        
        return Bensptr.objects.using(banco).get(
            bens_empr=empresa,
            bens_fili=filial,
            bens_codi=codigo
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        empresa = self.kwargs.get('bens_empr')
        filial = self.kwargs.get('bens_fili')
        if empresa:
            kwargs['empresa'] = int(empresa)
        if filial:
            kwargs['filial'] = int(filial)
        return kwargs

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        
        # Ajustar dados se necessário (ex: converter objetos para IDs)
        # O service update_bem itera sobre validated_data e faz setattr
        # Se Bensptr.bens_grup é IntegerField, setattr(bem, 'bens_grup', GrupobensObj) pode falhar se Django não converter.
        # Vamos garantir que passamos IDs.
        
        if dados.get('bens_grup'):
            dados['bens_grup'] = dados['bens_grup'].grup_codi
        if dados.get('bens_moti'):
            dados['bens_moti'] = dados['bens_moti'].moti_codi
        if dados.get('bens_forn'):
            dados['bens_forn'] = dados['bens_forn'].enti_clie
            
        BensptrService.update_bem(
            bem=self.object,
            validated_data=dados,
            using=banco,
        )
        
        slug = self.kwargs.get('slug')
        return redirect('bens_web:bens_list', slug=slug)
