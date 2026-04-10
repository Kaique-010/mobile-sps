import json
from decimal import Decimal
from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import UpdateView
import logging
logger = logging.getLogger(__name__)

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
        logger.info(f"Atualizacao Devolucao pk={self.kwargs.get(self.pk_url_kwarg)} banco={banco}")
        status_anterior = str(getattr(self.object, 'tdvl_stat', '0') or '0')
        itens_json = self.request.POST.get('itens_json') or '[]'
        try:
            itens = json.loads(itens_json)
        except Exception:
            itens = []
        logger.debug(f"Itens recebidos na atualização qtd={len(itens)}")
        dados = {k: v for k, v in form.cleaned_data.items()}
        tot_devo = sum(Decimal(str(it.get('itdv_vlor') or 0)) for it in itens)
        tot_repo = sum(Decimal(str(it.get('itdv_vlre') or 0)) for it in itens)
        dados['tdvl_tode'] = tot_devo
        dados['tdvl_tore'] = tot_repo
        dados['tdvl_safi'] = tot_devo - tot_repo
        logger.debug(f"Totais atualizados t_devo={dados['tdvl_tode']} t_repo={dados['tdvl_tore']} saldo={dados['tdvl_safi']}")
        try:
            logger.info(f"Chamando service.atualizar tdvl_nume={getattr(self.object, 'tdvl_nume', None)}")
            self.object = TrocaDevolucaoService.atualizar(
                banco,
                self.object,
                dados,
                processar_movimentacoes=False,
            )
        except Exception as e:
            logger.exception(f"Erro ao atualizar devolução: {e}")
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
        logger.debug(f"Itens existentes no banco para tdvl={getattr(self.object, 'tdvl_nume', None)}: {existentes}")
        if itens or (self.request.POST.get('itens_json') is not None):
            if itens or existentes == 0:
                try:
                    logger.info(f"Atualizando itens tdvl_nume={getattr(self.object, 'tdvl_nume', None)} qtd={len(itens)}")
                    TrocaDevolucaoService.atualizar_itens(banco, self.object, itens)
                except Exception as e:
                    logger.exception(f"Erro ao atualizar itens: {e}")
                    form.add_error(None, f"Erro ao salvar itens: {e}")
                    return self.form_invalid(form)
        status_atual = str(getattr(self.object, 'tdvl_stat', '0') or '0')
        itens_foram_postados = (self.request.POST.get('itens_json') is not None)
        if status_atual == '2' and (status_anterior != '2' or itens_foram_postados):
            try:
                logger.info(f"Concluindo devolução tdvl_nume={getattr(self.object, 'tdvl_nume', None)} status {status_anterior}->{status_atual} reprocessar_itens={itens_foram_postados}")
                TrocaDevolucaoService.concluir(banco, self.object)
            except Exception as e:
                logger.exception(f"Falha ao concluir: {e}")
                form.add_error('tdvl_stat', f"Falha ao concluir: {e}")
                return self.form_invalid(form)
        else:
            logger.info(f"Nao processa estoque tdvl_nume={getattr(self.object, 'tdvl_nume', None)} status={status_atual} status_anterior={status_anterior}")
        messages.success(self.request, f"Devolução/Troca #{getattr(self.object, 'tdvl_nume', '')} atualizada com sucesso.")
        slug = (self.kwargs.get('slug') or getattr(getattr(self.request, 'resolver_match', None), 'kwargs', {}).get('slug'))
        logger.info(f"Redirecionando para lista slug={slug}")
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
        logger.debug(f"Contexto atualização tdvl={self.object.tdvl_nume} itens_qtd={len(itens)}")
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
