from django.views.generic import CreateView
from django.contrib import messages
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Os
from ..forms import OsForm
from ..formssets import PecasOsFormSet, ServicoOsFormSet
from ...services.os_service import OsService

class OsCreateView(CreateView):
    model = Os
    form_class = OsForm
    template_name = 'Os/oscriar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/os/" if slug else "/web/home/"

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
            context['pecas_formset'] = PecasOsFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='pecas'
            )
            context['servicos_formset'] = ServicoOsFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='servicos'
            )
        else:
            context['pecas_formset'] = PecasOsFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='pecas'
            )
            context['servicos_formset'] = ServicoOsFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='servicos'
            )
        try:
            from Produtos.models import Produtos
            qs = Produtos.objects.using(banco).all()
            if empresa_id:
                qs = qs.filter(prod_empr=str(empresa_id))
            context['produtos'] = qs.order_by('prod_nome')[:500]
        except Exception:
            context['produtos'] = []
        context['slug'] = self.kwargs.get('slug')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        pecas_formset = context['pecas_formset']
        servicos_formset = context['servicos_formset']
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        banco = get_licenca_db_config(self.request) or 'default'
        if form.is_valid() and pecas_formset.is_valid() and servicos_formset.is_valid():
            try:
                os_data = form.cleaned_data.copy()
                os_data['os_empr'] = empresa_id
                os_data['os_fili'] = filial_id
                os_data['os_desc'] = os_data.get('os_desc', 0)
                os_data['os_tota'] = os_data.get('os_tota', 0)
                os_data.pop('os_topr', None)
                if not os_data.get('os_stat_os'):
                    os_data['os_stat_os'] = 0
                if hasattr(os_data.get('os_clie'), 'enti_clie'):
                    os_data['os_clie'] = os_data['os_clie'].enti_clie
                if hasattr(os_data.get('os_resp'), 'enti_clie'):
                    os_data['os_resp'] = os_data['os_resp'].enti_clie
                pecas_data = []
                for item_form in pecas_formset.forms:
                    if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                        continue
                    item_data = item_form.cleaned_data.copy()
                    prod = item_data.get('peca_prod')
                    prod_code = getattr(prod, 'prod_codi', prod)
                    pecas_data.append({
                        'peca_prod': prod_code,
                        'peca_quan': item_data.get('peca_quan', 1),
                        'peca_unit': item_data.get('peca_unit', 0),
                        'peca_desc': item_data.get('peca_desc', 0),
                    })
                servicos_data = []
                for item_form in servicos_formset.forms:
                    if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                        continue
                    item_data = item_form.cleaned_data.copy()
                    prod = item_data.get('serv_prod')
                    prod_code = getattr(prod, 'prod_codi', prod)
                    servicos_data.append({
                        'serv_prod': prod_code,
                        'serv_quan': item_data.get('serv_quan', 1),
                        'serv_unit': item_data.get('serv_unit', 0),
                        'serv_desc': item_data.get('serv_desc', 0),
                    })
                if not pecas_data and not servicos_data:
                    messages.error(self.request, "A OS precisa ter pelo menos uma peça ou serviço.")
                    return self.form_invalid(form)
                os = OsService.create_os(
                    banco,
                    os_data,
                    pecas_data,
                    servicos_data,
                )
                messages.success(self.request, f"OS {os.os_os} criada com sucesso.")
                return redirect(self.get_success_url())
            except Exception as e:
                messages.error(self.request, f"Erro ao salvar OS: {str(e)}")
                return self.form_invalid(form)
        else:
            if not form.is_valid():
                messages.error(self.request, f"Erros no formulário: {form.errors}")
            if not pecas_formset.is_valid() or not servicos_formset.is_valid():
                messages.error(self.request, "Erros nos itens de peças ou serviços.")
            return self.form_invalid(form)