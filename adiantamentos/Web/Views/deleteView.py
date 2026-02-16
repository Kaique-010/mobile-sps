from django.views.generic import DeleteView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Adiantamentos


class AdiantamentosDeleteView(DeleteView):
    model = Adiantamentos
    template_name = 'Adiantamentos/adiantamento_confirm_delete.html'

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

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.get_object()
        from ...services import AdiantamentosService
        AdiantamentosService.delete(obj, using=banco)
        slug = self.kwargs.get('slug')
        return redirect('adiantamentos_web:adiantamentos_list', slug=slug)

