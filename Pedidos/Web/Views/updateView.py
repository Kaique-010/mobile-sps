from django.views.generic import UpdateView
from django.http import Http404
import logging
from django.shortcuts import redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from ...models import PedidoVenda
from ...services.pedido_service import PedidoVendaService
from ..forms import PedidoVendaForm
from ..formssets import ItensPedidoFormSet


logger = logging.getLogger(__name__)


class PedidoUpdateView(UpdateView):
    model = PedidoVenda
    form_class = PedidoVendaForm
    template_name = 'Pedidos/pedidocriar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/pedidos/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        return PedidoVenda.objects.using(banco).filter(
            pedi_empr=int(empresa_id),
            pedi_fili=int(filial_id)
        )

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        try:
            pk = int(self.kwargs.get(self.pk_url_kwarg))
        except Exception:
            raise Http404("Pedido inválido")
        obj = queryset.filter(pedi_nume=pk).first()
        if not obj:
            raise Http404("Pedido não encontrado")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)

        if self.request.POST:
            context['formset'] = ItensPedidoFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        else:
            try:
                from ...models import Itenspedidovenda
                from Entidades.models import Entidades
                from Produtos.models import Produtos
                pedido = self.object
                logger.debug("[PedidoUpdateView.get_context_data] carregando itens do pedido=%s", getattr(pedido, 'pedi_nume', None))
                itens_qs = Itenspedidovenda.objects.using(banco).filter(
                    iped_empr=pedido.pedi_empr,
                    iped_fili=pedido.pedi_fili,
                    iped_pedi=str(pedido.pedi_nume)
                ).order_by('iped_item')
                initial = []
                codigos = []
                for i in itens_qs:
                    initial.append({
                        'iped_prod': i.iped_prod,
                        'iped_quan': i.iped_quan,
                        'iped_unit': i.iped_unit,
                        'iped_desc': i.iped_desc or 0,
                    })
                    codigos.append(i.iped_prod)
                logger.debug("[PedidoUpdateView.get_context_data] itens_qs=%d initial_forms=%d", len(list(itens_qs)), len(initial))

                cl = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_forn).values('enti_nome').first()
                ve = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_vend).values('enti_nome').first()
                context['cliente_display'] = f"{pedido.pedi_forn} - {cl.get('enti_nome')}" if cl else str(pedido.pedi_forn)
                context['vendedor_display'] = f"{pedido.pedi_vend} - {ve.get('enti_nome')}" if ve else str(pedido.pedi_vend)

                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: f"{p.prod_codi} - {p.prod_nome}" for p in produtos}
                for idx, init in enumerate(initial):
                    init['display_prod_text'] = prod_map.get(init.get('iped_prod'), init.get('iped_prod'))
                logger.debug("[PedidoUpdateView.get_context_data] prod_map_size=%d", len(prod_map))
            except Exception:
                initial = []
                logger.exception("[PedidoUpdateView.get_context_data] erro ao pré-popular itens")

            context['formset'] = ItensPedidoFormSet(
                initial=initial,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='form'
            )
            try:
                mf = context['formset'].management_form
                logger.debug("[PedidoUpdateView.get_context_data] TOTAL_FORMS=%s INITIAL_FORMS=%s", getattr(mf, 'initial', {}).get('TOTAL_FORMS'), getattr(mf, 'initial', {}).get('INITIAL_FORMS'))
            except Exception:
                logger.debug("[PedidoUpdateView.get_context_data] management_form indisponível")

        context['slug'] = self.kwargs.get('slug')
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset_itens = context['formset']

        banco = get_licenca_db_config(self.request) or 'default'

        logger.debug("[PedidoUpdateView] Form valid=%s Formset valid=%s", form.is_valid(), formset_itens.is_valid())
        if form.is_valid() and formset_itens.is_valid():
            try:
                pedido = self.object
                pedido_updates = form.cleaned_data.copy()

                if hasattr(pedido_updates.get('pedi_forn'), 'enti_clie'):
                    pedido_updates['pedi_forn'] = pedido_updates['pedi_forn'].enti_clie
                if hasattr(pedido_updates.get('pedi_vend'), 'enti_clie'):
                    pedido_updates['pedi_vend'] = pedido_updates['pedi_vend'].enti_clie

                logger.debug(
                    "[PedidoUpdateView] Atualização pedido pedi_nume=%s pedi_desc=%s pedi_topr=%s",
                    getattr(pedido, 'pedi_nume', None),
                    pedido_updates.get('pedi_desc'),
                    pedido_updates.get('pedi_topr'),
                )

                itens_data = []
                for item_form in formset_itens.forms:
                    if not item_form.cleaned_data:
                        continue
                    if item_form.cleaned_data.get('DELETE'):
                        continue
                    item_data = item_form.cleaned_data.copy()
                    if hasattr(item_data.get('iped_prod'), 'prod_codi'):
                        item_data['iped_prod'] = item_data['iped_prod'].prod_codi
                    logger.debug(
                        "[PedidoUpdateView] Item: prod=%s quan=%s unit=%s desc=%s",
                        item_data.get('iped_prod'),
                        item_data.get('iped_quan', 1),
                        item_data.get('iped_unit', 0),
                        item_data.get('iped_desc', 0),
                    )
                    itens_data.append({
                        'iped_prod': item_data.get('iped_prod'),
                        'iped_quan': item_data.get('iped_quan', 1),
                        'iped_unit': item_data.get('iped_unit', 0),
                        'iped_desc': item_data.get('iped_desc', 0),
                    })

                if not itens_data:
                    messages.error(self.request, "O pedido precisa ter pelo menos um item.")
                    return self.form_invalid(form)

                logger.debug("[PedidoUpdateView] Chamando service.update_pedido_venda com %d itens", len(itens_data))
                logger.debug("[PedidoUpdateView] tipo_oper=%s", pedido_updates.get('pedi_tipo_oper'))
                PedidoVendaService.update_pedido_venda(
                    banco,
                    pedido,
                    pedido_updates,
                    itens_data,
                    pedi_tipo_oper=pedido_updates.get('pedi_tipo_oper', 'VENDA')
                )
                logger.debug(
                    "[PedidoUpdateView] Pedido atualizado pedi_nume=%s pedi_topr=%s pedi_desc=%s pedi_tota=%s",
                    getattr(pedido, 'pedi_nume', None), getattr(pedido, 'pedi_topr', None), getattr(pedido, 'pedi_desc', None), getattr(pedido, 'pedi_tota', None)
                )
                messages.success(self.request, f"Pedido {pedido.pedi_nume} atualizado com sucesso.")
                return redirect(self.get_success_url())
            except Exception as e:
                messages.error(self.request, f"Erro ao atualizar pedido: {str(e)}")
                import traceback
                logger.exception("[PedidoUpdateView] Falha ao atualizar pedido: %s", e)
                traceback.print_exc()
                return self.form_invalid(form)
        else:
            if not form.is_valid():
                logger.error("[PedidoUpdateView] Erros no form: %s", form.errors)
                messages.error(self.request, f"Erros no formulário: {form.errors}")
            if not formset_itens.is_valid():
                logger.error("[PedidoUpdateView] Erros no formset: %s", formset_itens.errors)
                messages.error(self.request, f"Erros nos itens: {formset_itens.errors}")
            return self.form_invalid(form)
