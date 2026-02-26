from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from core.utils import get_licenca_db_config
from ..forms import GrupobensForm
from ...models import Grupobens
from ...Web.Services.registrar_bens import GrupobensService

class GrupobensListView(ListView):
    model = Grupobens
    template_name = 'Bens/Grupos/grupo_list.html'
    context_object_name = 'grupos'
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = self.request.session.get('empresa_id')
        
        qs = Grupobens.objects.using(banco).all()
        
        if empresa:
            qs = qs.filter(grup_empr=empresa)

        # Filtros
        nome = self.request.GET.get('grup_nome')
        codigo = self.request.GET.get('grup_codi')

        if nome:
            qs = qs.filter(grup_nome__icontains=nome)
        if codigo:
            qs = qs.filter(grup_codi=codigo)
            
        return qs.order_by('grup_nome')

class GrupobensCreateView(CreateView):
    model = Grupobens
    form_class = GrupobensForm
    template_name = 'Bens/Grupos/grupo_form.html'

    def form_valid(self, form):
        print(f"DEBUG: form_valid called with data: {form.cleaned_data}")
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        
        empresa = self.request.session.get('empresa_id')
        # Filial não é parte da PK de Grupobens (grup_empr, grup_codi), mas vamos ver se o service usa.
        # GrupobensService.criar_grupo usa dados['grup_empr']
        
        if empresa:
            dados['grup_empr'] = int(empresa)
            
        try:
            grupo = GrupobensService.criar_grupo(
                dados=dados,
                using=banco,
            )
            print(f"DEBUG: Grupo created successfully: {grupo}")
        except Exception as e:
            print(f"DEBUG: Error creating grupo: {e}")
            import traceback
            traceback.print_exc()
            form.add_error(None, f"Erro ao salvar: {e}")
            return self.form_invalid(form)

        slug = self.kwargs.get('slug')
        return redirect('bens_web:grupo_list', slug=slug)

    def form_invalid(self, form):
        print(f"DEBUG: form_invalid called with errors: {form.errors}")
        return super().form_invalid(form)

class GrupobensUpdateView(UpdateView):
    model = Grupobens
    form_class = GrupobensForm
    template_name = 'Bens/Grupos/grupo_form.html'

    def get_object(self, queryset=None):
        empresa = self.kwargs.get('grup_empr')
        codigo = self.kwargs.get('grup_codi')
        banco = get_licenca_db_config(self.request) or 'default'
        
        return Grupobens.objects.using(banco).get(
            grup_empr=empresa,
            grup_codi=codigo
        )

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        
        GrupobensService.update_grupo(
            grupo=self.object,
            validated_data=dados,
            using=banco,
        )
        
        slug = self.kwargs.get('slug')
        return redirect('bens_web:grupo_list', slug=slug)

class GrupobensDeleteView(DeleteView):
    model = Grupobens
    template_name = 'Bens/Grupos/grupo_confirm_delete.html'

    def get_object(self, queryset=None):
        empresa = self.kwargs.get('grup_empr')
        codigo = self.kwargs.get('grup_codi')
        banco = get_licenca_db_config(self.request) or 'default'
        
        return Grupobens.objects.using(banco).get(
            grup_empr=empresa,
            grup_codi=codigo
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        banco = get_licenca_db_config(self.request) or 'default'
        
        GrupobensService.delete(self.object, using=banco)
        
        slug = self.kwargs.get('slug')
        return redirect('bens_web:grupo_list', slug=slug)
