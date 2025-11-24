from django.views.generic import UpdateView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..mixin import DBAndSlugMixin
from ..forms import TitulosReceberForm
from ...models import Titulosreceber


class TitulosReceberUpdateView(DBAndSlugMixin, UpdateView):
    model = Titulosreceber
    form_class = TitulosReceberForm
    template_name = 'ContasAReceber/titulo_receber_editar.html'

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
        parcela = self.kwargs.get('titu_parc')
        qs = Titulosreceber.objects.using(banco).filter(titu_titu=titu)
        if emp:
            qs = qs.filter(titu_empr=int(emp))
        if fil:
            qs = qs.filter(titu_fili=int(fil))
        if parcela:
            qs = qs.filter(titu_parc=parcela)
        obj = qs.order_by('titu_parc','titu_venc').first()
        if not obj:
            from django.http import Http404
            raise Http404('Título a receber não encontrado')
        return obj

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.get_object()
        dados = form.cleaned_data

        emp = (self.request.session.get('empresa_id')
               or self.request.headers.get('X-Empresa')
               or getattr(self, 'empresa_id', None)
               or obj.titu_empr)
        fil = (self.request.session.get('filial_id')
               or self.request.headers.get('X-Filial')
               or getattr(self, 'filial_id', None)
               or obj.titu_fili)
        if emp is not None:
            try:
                dados['titu_empr'] = int(emp)
            except Exception:
                dados['titu_empr'] = emp
        if fil is not None:
            try:
                dados['titu_fili'] = int(fil)
            except Exception:
                dados['titu_fili'] = fil

        from ...services import atualizar_titulo_receber
        atualizar_titulo_receber(obj, banco=banco, dados=dados)
        return redirect('contas_a_receber_web:titulos_receber_list', slug=self.slug)