from django.views.generic import CreateView
import logging
from django.shortcuts import redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from ...models import PedidoVenda
from ...services.pedido_service import PedidoVendaService
from ..forms import PedidoVendaForm
from ..formssets import ItensPedidoFormSet




logger = logging.getLogger(__name__)


class PedidoCreateView(CreateView):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)

        if self.request.POST:
            context['formset'] = ItensPedidoFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='form'
            )
        else:
            context['formset'] = ItensPedidoFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='form'
            )

        try:
            from Produtos.models import Produtos
            qs = Produtos.objects.using(banco).all()
            if empresa_id:
                qs = qs.filter(prod_empr=str(empresa_id))
            context['produtos'] = qs.order_by('prod_nome')[:500]
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            context['produtos'] = []

        context['slug'] = self.kwargs.get('slug')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset_itens = context['formset']

        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        banco = get_licenca_db_config(self.request) or 'default'

        logger.debug("[PedidoCreateView] Form valid=%s Formset valid=%s", form.is_valid(), formset_itens.is_valid())
        if form.is_valid() and formset_itens.is_valid():
            try:
                pedido_data = form.cleaned_data.copy()
                pedido_data['pedi_empr'] = empresa_id
                pedido_data['pedi_fili'] = filial_id
                pedido_data['pedi_desc'] = pedido_data.get('pedi_desc', 0)
                pedido_data['pedi_topr'] = pedido_data.get('pedi_topr', 0)

                if hasattr(pedido_data.get('pedi_forn'), 'enti_clie'):
                    pedido_data['pedi_forn'] = pedido_data['pedi_forn'].enti_clie
                if hasattr(pedido_data.get('pedi_vend'), 'enti_clie'):
                    pedido_data['pedi_vend'] = pedido_data['pedi_vend'].enti_clie

                logger.debug(
                    "[PedidoCreateView] Dados do pedido iniciais: pedi_forn=%s pedi_vend=%s pedi_desc=%s pedi_topr=%s",
                    getattr(pedido_data.get('pedi_forn'), 'enti_clie', pedido_data.get('pedi_forn')),
                    getattr(pedido_data.get('pedi_vend'), 'enti_clie', pedido_data.get('pedi_vend')),
                    pedido_data.get('pedi_desc'),
                    pedido_data.get('pedi_topr'),
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
                        "[PedidoCreateView] Item: prod=%s quan=%s unit=%s desc=%s",
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

                logger.debug("[PedidoCreateView] Chamando service.create_pedido_venda com %d itens", len(itens_data))
                pedi_tipo_oper = pedido_data.get('pedi_tipo_oper', 'VENDA')
                logger.debug("[PedidoCreateView] tipo_oper=%s", pedi_tipo_oper)
                pedido = PedidoVendaService.create_pedido_venda(
                    banco,
                    pedido_data,
                    itens_data,
                    pedi_tipo_oper=pedi_tipo_oper
                )
                logger.debug(
                    "[PedidoCreateView] Pedido criado pedi_nume=%s pedi_topr=%s pedi_desc=%s pedi_tota=%s",
                    getattr(pedido, 'pedi_nume', None), getattr(pedido, 'pedi_topr', None), getattr(pedido, 'pedi_desc', None), getattr(pedido, 'pedi_tota', None)
                )
                messages.success(self.request, f"Pedido {pedido.pedi_nume} criado com sucesso.")
                return redirect(self.get_success_url())

            except Exception as e:
                messages.error(self.request, f"Erro ao salvar pedido: {str(e)}")
                logger.exception("[PedidoCreateView] Falha ao salvar pedido: %s", e)
                import traceback
                traceback.print_exc()
                return self.form_invalid(form)
        else:
            if not form.is_valid():
                messages.error(self.request, f"Erros no formulário: {form.errors}")
            if not formset_itens.is_valid():
                messages.error(self.request, f"Erros nos itens: {formset_itens.errors}")
            return self.form_invalid(form)
        