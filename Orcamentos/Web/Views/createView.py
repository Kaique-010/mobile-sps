from django.views.generic import CreateView
from django.shortcuts import redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from Pedidos.services.pedido_service import PedidoVendaService, OrcamentoService
from ..forms import OrcamentoVendaForm
from ..formssets import ItensOrcamentoFormSet
from ...models import Orcamentos, ItensOrcamento

class OrcamentoCreateView(CreateView):
    model = Orcamentos
    form_class = OrcamentoVendaForm
    template_name = 'Orcamentos/orcamentocriar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/orcamentos/" if slug else "/web/home/"

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
            context['formset'] = ItensOrcamentoFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='form'
            )
        else:
            context['formset'] = ItensOrcamentoFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='form'
            )
        context['slug'] = self.kwargs.get('slug')
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        formset = ItensOrcamentoFormSet(
            self.request.POST,
            form_kwargs={'database': banco, 'empresa_id': empresa_id},
            prefix='form'
        )
        if not formset.is_valid():
            messages.error(self.request, 'Verifique os itens do orçamento.')
            return self.form_invalid(form)
        # Monta dados do orçamento para o serviço
        orcamento_data = {
            'pedi_empr': empresa_id,
            'pedi_fili': filial_id,
            'pedi_data': form.cleaned_data.get('pedi_data'),
            'pedi_forn': form.cleaned_data.get('pedi_forn'),
            'pedi_vend': form.cleaned_data.get('pedi_vend'),
            'pedi_desc': form.cleaned_data.get('pedi_desc') or 0,
            'pedi_stat': form.cleaned_data.get('pedi_stat') or '0',
            'pedi_obse': form.cleaned_data.get('pedi_obse'),
        }

        # Extrai itens do formset (sem cálculos)
        itens_data = []
        for item_form in formset:
            cd = getattr(item_form, 'cleaned_data', {}) or {}
            if not cd or cd.get('DELETE'):
                continue
            itens_data.append({
                'iped_prod': str(cd.get('iped_prod') or ''),
                'iped_quan': PedidoVendaService._to_decimal(cd.get('iped_quan')),
                'iped_unit': PedidoVendaService._to_decimal(cd.get('iped_unit')),
                'iped_desc': PedidoVendaService._to_decimal(0),
            })

        if not itens_data:
            messages.error(self.request, 'Inclua ao menos um item válido no orçamento.')
            return self.form_invalid(form)

        # Cria via serviço
        orc = OrcamentoService.create_orcamento(banco=banco, orcamento_data=orcamento_data, itens_data=itens_data)
        messages.success(self.request, f'Orçamento #{orc.pedi_nume} criado com sucesso.')
        return redirect(self.get_success_url())