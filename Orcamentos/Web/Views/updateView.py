from django.views.generic import UpdateView
from django.shortcuts import redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from Pedidos.services.pedido_service import PedidoVendaService, OrcamentoService
from ..forms import OrcamentoVendaForm
from ..formssets import ItensOrcamentoFormSet
from ...models import Orcamentos, ItensOrcamento

class OrcamentoUpdateView(UpdateView):
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

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Orcamentos.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        if self.request.POST:
            context['formset'] = ItensOrcamentoFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        else:
            try:
                from Entidades.models import Entidades
                from Produtos.models import Produtos
                obj = self.object
                itens_qs = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=obj.pedi_empr, iped_fili=obj.pedi_fili, iped_pedi=str(obj.pedi_nume)
                ).order_by('iped_item')
                initial = []
                codigos = []
                for i in itens_qs:
                    initial.append({
                        'iped_prod': i.iped_prod,
                        'iped_quan': i.iped_quan,
                        'iped_unit': i.iped_unit,
                    })
                    codigos.append(i.iped_prod)
                cl = Entidades.objects.using(banco).filter(enti_clie=obj.pedi_forn).values('enti_nome').first()
                ve = Entidades.objects.using(banco).filter(enti_clie=obj.pedi_vend).values('enti_nome').first()
                context['cliente_display'] = f"{obj.pedi_forn} - {cl.get('enti_nome')}" if cl else str(obj.pedi_forn)
                context['vendedor_display'] = f"{obj.pedi_vend} - {ve.get('enti_nome')}" if ve else str(obj.pedi_vend)
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: f"{p.prod_codi} - {p.prod_nome}" for p in produtos}
                for init in initial:
                    init['display_prod_text'] = prod_map.get(init.get('iped_prod'), init.get('iped_prod'))
            except Exception:
                initial = []
            context['formset'] = ItensOrcamentoFormSet(
                initial=initial,
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        context['slug'] = self.kwargs.get('slug')
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        formset = ItensOrcamentoFormSet(self.request.POST, form_kwargs={'database': banco, 'empresa_id': empresa_id})
        if not formset.is_valid():
            messages.error(self.request, 'Verifique os itens do orçamento.')
            return self.form_invalid(form)
        # Extrai itens
        obj = self.object
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

        # Monta updates
        updates = {
            'pedi_data': form.cleaned_data.get('pedi_data'),
            'pedi_forn': form.cleaned_data.get('pedi_forn'),
            'pedi_vend': form.cleaned_data.get('pedi_vend'),
            'pedi_desc': form.cleaned_data.get('pedi_desc') or 0,
            'pedi_stat': form.cleaned_data.get('pedi_stat') or getattr(obj, 'pedi_stat', '0'),
            'pedi_obse': form.cleaned_data.get('pedi_obse'),
        }

        OrcamentoService.update_orcamento(banco=banco, orcamento_obj=obj, updates=updates, itens_data=itens_data)
        messages.success(self.request, f'Orçamento #{obj.pedi_nume} atualizado com sucesso.')
        return redirect(self.get_success_url())