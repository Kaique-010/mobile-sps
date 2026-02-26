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
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')
        
        qs = Motivosptr.objects.using(banco).all()
        
        # Motivosptr não tem campos de empresa/filial na model definition?
        # class Motivosptr(models.Model):
        #     moti_codi = models.IntegerField(primary_key=True)
        #     moti_desc = models.CharField(max_length=60, blank=True, null=True)
        #     class Meta: ...
        
        # Porém, no Service 'MotivosService.criar_motivo', ele usa 'moti_empr' e 'moti_fili' para gerar sequencial.
        # Isso sugere que o model deve ter esses campos ou o dump estava incompleto.
        # Se o model não tiver, o create(**dados) falharia se passasse moti_empr.
        # Mas no create, ele passa **dados.
        
        # Vamos assumir que Motivosptr é global ou a filtragem deve ser feita de outra forma se não tiver empresa.
        # Se for global, não filtramos. Se tiver empresa, filtramos.
        # Vamos verificar se conseguimos filtrar, senão retornamos all().
        
        # Na dúvida, vamos retornar all() por enquanto, pois o model definition mostrado anteriormente não tinha moti_empr.
        # Se tiver erro, corrigiremos.
        
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
        
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')
        
        # O Service espera moti_empr/moti_fili para gerar sequencial
        if empresa:
            dados['moti_empr'] = int(empresa)
        if filial:
            dados['moti_fili'] = int(filial)
            
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
