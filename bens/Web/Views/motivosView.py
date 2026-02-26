from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..forms import MotivosptrForm
from ...models import Motivosptr
from ...Web.Services.registrar_bens import MotivosService

class MotivosptrListView(ListView):
    model = Motivosptr
    template_name = 'Bens/Motivos/motivo_list.html'
    context_object_name = 'motivos'
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        
        
        qs = Motivosptr.objects.using(banco).all()
        

        
        nome = self.request.GET.get('moti_desc')
        if nome:
            qs = qs.filter(moti_desc__icontains=nome)
            
        return qs.order_by('moti_desc')

class MotivosptrCreateView(CreateView):
    model = Motivosptr
    form_class = MotivosptrForm
    template_name = 'Bens/Motivos/motivo_form.html'

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        

            
        MotivosService.criar_motivo(
            dados=dados,
            using=banco,
        )

        slug = self.kwargs.get('slug')
        return redirect('bens_web:motivo_list', slug=slug)

class MotivosptrUpdateView(UpdateView):
    model = Motivosptr
    form_class = MotivosptrForm
    template_name = 'Bens/Motivos/motivo_form.html'

    def get_object(self, queryset=None):
        codigo = self.kwargs.get('moti_codi')
        banco = get_licenca_db_config(self.request) or 'default'
        
        return Motivosptr.objects.using(banco).get(moti_codi=codigo)

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        
        MotivosService.update_motivo(
            motivo=self.object,
            validated_data=dados,
            using=banco,
        )
        
        slug = self.kwargs.get('slug')
        return redirect('bens_web:motivo_list', slug=slug)

class MotivosptrDeleteView(DeleteView):
    model = Motivosptr
    template_name = 'Bens/Motivos/motivo_confirm_delete.html'

    def get_object(self, queryset=None):
        codigo = self.kwargs.get('moti_codi')
        banco = get_licenca_db_config(self.request) or 'default'
        
        return Motivosptr.objects.using(banco).get(moti_codi=codigo)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        banco = get_licenca_db_config(self.request) or 'default'
        
        MotivosService.delete(self.object, using=banco)
        
        slug = self.kwargs.get('slug')
        return redirect('bens_web:motivo_list', slug=slug)
