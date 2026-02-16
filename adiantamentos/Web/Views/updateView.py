from django.views.generic import UpdateView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..forms import AdiantamentosForm
from ...models import Adiantamentos


class AdiantamentosUpdateView(UpdateView):
    model = Adiantamentos
    form_class = AdiantamentosForm
    template_name = 'Adiantamentos/adiantamento_editar.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Adiantamentos.objects.using(banco).all()

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        empresa = self.request.session.get('empresa_id')
        entidade = self.kwargs.get('adia_enti')
        documento = self.kwargs.get('adia_docu')
        serie = self.kwargs.get('adia_seri')

        if empresa:
            queryset = queryset.filter(adia_empr=int(empresa))

        queryset = queryset.filter(
            adia_enti=entidade,
            adia_docu=documento,
            adia_seri=serie,
        )
        obj = queryset.first()
        if not obj:
            from django.http import Http404
            raise Http404('Adiantamento não encontrado')
        return obj

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.get_object()
        dados = form.cleaned_data
        from ...services import AdiantamentosService
        AdiantamentosService.update(obj, dados, using=banco)
        slug = self.kwargs.get('slug')
        return redirect('adiantamentos_web:adiantamentos_list', slug=slug)

