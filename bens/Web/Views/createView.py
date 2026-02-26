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
        print(f"DEBUG: form_valid called with data: {form.cleaned_data}")
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')

        if empresa:
            dados['bens_empr'] = int(empresa)
        if filial:
            dados['bens_fili'] = int(filial)
            
        # Converter objetos relacionados para IDs se o Service esperar IDs
        # O Form já limpa para IDs nos métodos clean_*, mas se passar pelo form.save, ele pode tentar salvar o objeto
        # BensptrForm é ModelForm.
        # Mas aqui chamamos BensptrService.criar_bem.
        
        # Como adicionamos clean_bens_grup no form, o cleaned_data['bens_grup'] já deve ser o ID (int) ou None.
        # Verificamos para garantir.
        
        print(f"DEBUG: dados['bens_grup'] type: {type(dados.get('bens_grup'))} value: {dados.get('bens_grup')}")
        
        # Se clean_* funcionou, não precisamos acessar .grup_codi aqui, pois já é int.
        # Se for objeto, acessamos.
        
        if hasattr(dados.get('bens_grup'), 'grup_codi'):
             dados['bens_grup'] = dados['bens_grup'].grup_codi
             
        if hasattr(dados.get('bens_moti'), 'moti_codi'):
             dados['bens_moti'] = dados['bens_moti'].moti_codi

        if hasattr(dados.get('bens_forn'), 'enti_clie'):
             dados['bens_forn'] = dados['bens_forn'].enti_clie
        elif hasattr(dados.get('bens_forn'), 'enti_codi'): # Se for Entidades, pode ser enti_codi ou enti_clie a chave?
             # Entidades model: enti_codi (char) não é PK?
             # Vamos checar Entidades model se necessário. Mas o form clean usa enti_clie? Não, usa enti_codi no clean anterior que fiz.
             # Vou corrigir form clean para usar enti_codi se for o que salva no banco.
             pass

        try:
            self.object = BensptrService.criar_bem(
                dados=dados,
                using=banco,
            )
            print(f"DEBUG: Bem created successfully: {self.object}")
        except Exception as e:
            print(f"DEBUG: Error creating bem: {e}")
            import traceback
            traceback.print_exc()
            form.add_error(None, f"Erro ao salvar: {e}")
            return self.form_invalid(form)

        slug = self.kwargs.get('slug')
        # Redirecionar para lista
        # Precisamos definir o namespace 'bens_web' no urls.py
        return redirect('bens_web:bens_list', slug=slug)

    def form_invalid(self, form):
        print(f"DEBUG: form_invalid called with errors: {form.errors}")
        return super().form_invalid(form)
