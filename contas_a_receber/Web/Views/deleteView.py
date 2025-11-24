from django.views.generic import DeleteView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Titulosreceber


class TitulosReceberDeleteView(DeleteView):
    model = Titulosreceber
    slug_field = 'titu_titu'
    slug_url_kwarg = 'titu_titu'
    template_name = 'ContasAReceber/titulo_receber_confirm_delete.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        qs = Titulosreceber.objects.using(banco).all()
        emp = self.request.session.get('empresa_id')
        fil = self.request.session.get('filial_id')
        if emp:
            qs = qs.filter(titu_empr=int(emp))
        if fil:
            qs = qs.filter(titu_fili=int(fil))
        return qs

    def get_object(self, queryset=None):
        banco = get_licenca_db_config(self.request) or 'default'
        emp = self.request.session.get('empresa_id')
        fil = self.request.session.get('filial_id')
        titu = self.kwargs.get('titu_titu')
        qs = Titulosreceber.objects.using(banco).filter(titu_titu=titu)
        if emp:
            qs = qs.filter(titu_empr=int(emp))
        if fil:
            qs = qs.filter(titu_fili=int(fil))
        obj = qs.order_by('titu_parc','titu_venc').first()
        if not obj:
            from django.http import Http404
            raise Http404('Título a receber não encontrado')
        return obj

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.get_object()
        from ...services import excluir_titulo_receber
        excluir_titulo_receber(obj, banco=banco)
        return redirect('contas_a_receber_web:titulos_receber_list', slug=self.kwargs.get('slug'))