from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import UpdateView

from ...models import Ordemproducao
from ...services import OrdemProducaoFilhosService, OrdemProducaoService
from ..forms import OrdemproducaoForm
from .base import OrdemProducaoWebMixin


class OrdemproducaoUpdateView(OrdemProducaoWebMixin, UpdateView):
    model = Ordemproducao
    form_class = OrdemproducaoForm
    template_name = 'OrdemProducao/ordemproducao_form.html'
    pk_url_kwarg = 'orpr_codi'

    def get_queryset(self):
        return Ordemproducao.objects.using(self.get_banco()).all()

    def form_valid(self, form):
        banco = self.get_banco()
        self.object = form.save(commit=False)
        try:
            antigo = Ordemproducao.objects.using(banco).get(pk=self.object.pk)
            antigo_status = antigo.orpr_stat
        except Ordemproducao.DoesNotExist:
            antigo_status = None
        self.object.save(using=banco)
        if self.object.orpr_stat == '2' and not OrdemProducaoService.finalizacao_processada(ordem=self.object, using=banco):
            usua = int(self.request.session.get("usua_codi") or 0)
            OrdemProducaoService.finalizar_ordem(ordem=self.object, using=banco, usua=usua)
        elif self.object.orpr_stat == '1' and antigo_status != '1':
            OrdemProducaoService.iniciar_producao(ordem=self.object, using=banco)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('ordem_producao_web:ordemproducao_list', kwargs={'slug': self.get_slug()})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self.get_banco()
        ordem = self.object
        context['cliente_nome'] = OrdemProducaoService.buscar_cliente_nome(using=banco, ordem=ordem) or ''
        context['vendedor_nome'] = OrdemProducaoService.buscar_vendedor(using=banco, ordem=ordem) or ''
        context['produto_nome'] = OrdemProducaoService.buscar_produto_nome(using=banco, empresa_id=ordem.orpr_empr, codigo=ordem.orpr_prod) or ''
        context['materiais_previstos'] = OrdemProducaoFilhosService.listar_materiais_previstos(ordem=ordem, using=banco)
        context['movimentacoes_etapa'] = OrdemProducaoFilhosService.listar_movimentacoes_etapa(ordem=ordem, using=banco)
        saldos = OrdemProducaoFilhosService.listar_movimentacoes_saldo(ordem=ordem, using=banco)
        codigos = [str(s.moet_peso_prod) for s in saldos]
        labels = OrdemProducaoService.map_produtos_nomes(using=banco, empresa_id=ordem.orpr_empr, codigos=codigos)
        context['movimentacoes_saldo'] = [
            {
                "produto_codigo": str(s.moet_peso_prod),
                "produto_label": labels.get(str(s.moet_peso_prod), str(s.moet_peso_prod)),
                "previsto": s.moet_peso_codi or 0,
                "usado": s.moet_peso_moet or 0,
                "saldo": s.moet_peso_sald if s.moet_peso_sald is not None else ((s.moet_peso_codi or 0) - (s.moet_peso_moet or 0)),
            }
            for s in saldos
        ]
        return context
