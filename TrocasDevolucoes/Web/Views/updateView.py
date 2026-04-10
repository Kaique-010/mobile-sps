import json
from decimal import Decimal
from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import UpdateView

from core.utils import get_licenca_db_config
from TrocasDevolucoes.Web.forms import TrocaDevolucaoForm
from TrocasDevolucoes.models import TrocaDevolucao
from TrocasDevolucoes.services.troca_devolucao_service import TrocaDevolucaoService


class DevolucaoUpdateView(UpdateView):
    form_class = TrocaDevolucaoForm
    template_name = 'TrocasDevolucoes/devolucao_form.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return TrocaDevolucao.objects.using(banco).all()

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request)
        itens_json = self.request.POST.get('itens_json') or '[]'
        try:
            itens = json.loads(itens_json)
        except Exception:
            itens = []
        dados = {k: v for k, v in form.cleaned_data.items()}
        tot_devo = sum(Decimal(str(it.get('itdv_vlor') or 0)) for it in itens)
        tot_repo = sum(Decimal(str(it.get('itdv_vlre') or 0)) for it in itens)
        dados['tdvl_tode'] = tot_devo
        dados['tdvl_tore'] = tot_repo
        dados['tdvl_safi'] = tot_devo - tot_repo
        try:
            self.object = TrocaDevolucaoService.atualizar(
                banco,
                self.object,
                dados,
            )
        except Exception as e:
            form.add_error(None, f"Erro ao salvar: {e}")
            return self.form_invalid(form)
        try:
            from TrocasDevolucoes.models import ItensTrocaDevolucao
            existentes = ItensTrocaDevolucao.objects.using(banco).filter(
                itdv_empr=self.object.tdvl_empr,
                itdv_fili=self.object.tdvl_fili,
                itdv_tdvl=self.object.tdvl_nume,
            ).count()
        except Exception:
            existentes = 0
        if itens or (self.request.POST.get('itens_json') is not None):
            if itens or existentes == 0:
                try:
                    TrocaDevolucaoService.atualizar_itens(banco, self.object, itens)
                except Exception as e:
                    form.add_error(None, f"Erro ao salvar itens: {e}")
                    return self.form_invalid(form)
        messages.success(self.request, f"Devolução/Troca #{getattr(self.object, 'tdvl_nume', '')} atualizada com sucesso.")
        slug = (self.kwargs.get('slug') or getattr(getattr(self.request, 'resolver_match', None), 'kwargs', {}).get('slug'))
        return redirect('TrocasDevolucoesWeb:devolucoes_listar', slug=slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        context['titulo'] = f'Editar Devolução #{self.object.tdvl_nume}'
        banco = get_licenca_db_config(self.request)
        from TrocasDevolucoes.models import ItensTrocaDevolucao
        itens = list(
            ItensTrocaDevolucao.objects.using(banco)
            .filter(
                itdv_empr=self.object.tdvl_empr,
                itdv_fili=self.object.tdvl_fili,
                itdv_tdvl=self.object.tdvl_nume,
            )
            .values('itdv_item', 'itdv_pror', 'itdv_qtor', 'itdv_vlor', 'itdv_prre', 'itdv_qtre', 'itdv_vlre')
        )
        if self.request.method == 'POST':
            try:
                posted = self.request.POST.get('itens_json')
                if posted:
                    context['itens_json'] = json.loads(posted)
                else:
                    context['itens_json'] = itens
            except Exception:
                context['itens_json'] = itens
        else:
            context['itens_json'] = itens
        context['empresa'] = self.request.session.get('empresa') or self.request.session.get('empr') or self.object.tdvl_empr
        context['filial'] = self.request.session.get('filial') or self.request.session.get('fili') or self.object.tdvl_fili
        return context
