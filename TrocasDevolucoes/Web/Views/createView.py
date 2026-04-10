import json
from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import CreateView
import logging
logger = logging.getLogger(__name__)

from core.utils import get_licenca_db_config
from TrocasDevolucoes.Web.forms import TrocaDevolucaoForm
from TrocasDevolucoes.services.troca_devolucao_service import TrocaDevolucaoService


class DevolucaoCreateView(CreateView):
    form_class = TrocaDevolucaoForm
    template_name = 'TrocasDevolucoes/devolucao_form.html'

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request)
        logger.info(f"Criacao Devolucao banco={banco}")
        dados = form.cleaned_data
        empresa = self.request.session.get('empresa') or self.request.session.get('empr') or 1
        filial = self.request.session.get('filial') or self.request.session.get('fili') or 1
        dados['tdvl_empr'] = int(empresa)
        dados['tdvl_fili'] = int(filial)
        logger.debug(f"Contexto criacao empr={dados['tdvl_empr']} fili={dados['tdvl_fili']} tipo={dados.get('tdvl_tipo')} status={dados.get('tdvl_stat')}")
        itens_json = self.request.POST.get('itens_json') or '[]'
        try:
            itens = json.loads(itens_json)
        except Exception:
            itens = []
        logger.debug(f"Itens recebidos na criação qtd={len(itens)}")
        try:
            logger.info("Chamando service.criar_com_itens")
            self.object = TrocaDevolucaoService.criar_com_itens(banco, dados=dados, itens=itens)
        except Exception as e:
            logger.exception(f"Erro ao criar devolução: {e}")
            form.add_error(None, f"Erro ao salvar: {e}")
            return self.form_invalid(form)
        messages.success(self.request, f"Devolução/Troca #{getattr(self.object, 'tdvl_nume', '')} criada com sucesso.")
        slug = (self.kwargs.get('slug') or getattr(getattr(self.request, 'resolver_match', None), 'kwargs', {}).get('slug'))
        logger.info(f"Redirecionando para lista slug={slug}")
        return redirect('TrocasDevolucoesWeb:devolucoes_listar', slug=slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        context['titulo'] = 'Nova Devolução'
        context['empresa'] = self.request.session.get('empresa') or self.request.session.get('empr') or 1
        context['filial'] = self.request.session.get('filial') or self.request.session.get('fili') or 1
        if self.request.method == 'POST':
            try:
                posted = self.request.POST.get('itens_json')
                if posted:
                    context['itens_json'] = json.loads(posted)
                    logger.debug(f"Contexto criacao com itens_postados qtd={len(context['itens_json'])}")
            except Exception:
                pass
        return context
