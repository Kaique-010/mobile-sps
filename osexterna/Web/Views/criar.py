from django.views.generic import CreateView
from django.contrib import messages
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Osexterna, Servicososexterna
from ..forms import OsexternaForm, ServicososexternaForm
from ..formssets import ServicososexternaFormSet
from ...services.entidade_dados import DadosEntidadesService
from django.db.models import Max

class OsCreateView(CreateView):
    model = Osexterna
    form_class = OsexternaForm
    template_name = 'Osexterna/criar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/osexterna/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        kwargs['filial_id'] = self.request.session.get('filial_id', 1)
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        if self.request.POST:
            context['servicos_formset'] = ServicososexternaFormSet(
                data=self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id, 'filial_id': filial_id},
                prefix='servicos'
            )
        else:
            context['servicos_formset'] = ServicososexternaFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id, 'filial_id': filial_id},
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
        servicos_formset = context['servicos_formset']
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        banco = get_licenca_db_config(self.request) or 'default'
        if form.is_valid() and servicos_formset.is_valid():
            try:
                os_data = form.cleaned_data.copy()
                os_data['osex_empr'] = empresa_id
                os_data['osex_fili'] = filial_id
                if not os_data.get('osex_stat'):
                    os_data['osex_stat'] = 0
                if hasattr(os_data.get('osex_clie'), 'enti_clie'):
                    os_data['osex_clie'] = os_data['osex_clie'].enti_clie
                if hasattr(os_data.get('osex_resp'), 'enti_clie'):
                    os_data['osex_resp'] = os_data['osex_resp'].enti_clie
                servicos_data = []
                for item_form in servicos_formset.forms:
                    if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                        continue
                    item_data = item_form.cleaned_data.copy()
                    prod = item_data.get('serv_prod')
                    prod_code = getattr(prod, 'prod_codi', prod)
                    quan = item_data.get('serv_quan', 1) or 1
                    unit = item_data.get('serv_valo_unit', 0) or 0
                    total = (float(quan) or 0) * (float(unit) or 0)
                    servicos_data.append({
                        'serv_prod': prod_code,
                        'serv_quan': quan,
                        'serv_valo_unit': unit,
                        'serv_valo_tota': total,
                        'serv_desc': item_data.get('serv_desc', '')
                    })

                if not servicos_data:
                    messages.error(self.request, "A OS precisa ter pelo menos um serviço.")
                    return self.form_invalid(form)
                next_cod = (Osexterna.objects.using(banco).aggregate(Max('osex_codi'))['osex_codi__max'] or 0) + 1
                os_data['osex_codi'] = next_cod
                instance = Osexterna.objects.using(banco).create(**os_data)
                instance = DadosEntidadesService.preencher_dados_do_cliente(instance, self.request)
                instance.save(using=banco)
                # salvar serviços vinculados
                try:
                    last_seq = (Servicososexterna.objects.using(banco)
                                .filter(serv_empr=empresa_id, serv_fili=filial_id, serv_os=instance.osex_codi)
                                .aggregate(Max('serv_sequ'))['serv_sequ__max'] or 0)
                except Exception:
                    last_seq = 0
                seq = last_seq
                for item in servicos_data:
                    seq += 1
                    Servicososexterna.objects.using(banco).create(
                        serv_empr=empresa_id,
                        serv_fili=filial_id,
                        serv_os=instance.osex_codi,
                        serv_sequ=seq,
                        serv_desc=item.get('serv_desc', ''),
                        serv_quan=item.get('serv_quan') or 0,
                        serv_valo_unit=item.get('serv_valo_unit') or 0,
                        serv_valo_tota=item.get('serv_valo_tota') or 0,
                    )
                messages.success(self.request, f"OS Externa {instance.osex_codi} criada com sucesso.")
                return redirect(self.get_success_url())
            except Exception as e:
                messages.error(self.request, f"Erro ao salvar OS: {str(e)}")
                return self.form_invalid(form)
        else:
            if not form.is_valid():
                messages.error(self.request, f"Erros no formulário: {form.errors}")
            if not servicos_formset.is_valid():
                messages.error(self.request, "Erros nos itens de serviços.")
            return self.form_invalid(form)
