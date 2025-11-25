import os
from django.views.generic import TemplateView, UpdateView, ListView
from django.urls import reverse_lazy
from django.http import JsonResponse
from core.registry import get_licenca_db_config
from Entidades.models import Entidades
from ..forms.banco_config_form import BancoConfigForm
from ..forms.carteira_form import CNAB_CHOICES
from ...services.validation_service import validate_caixa_config


class ListaBancosView(TemplateView):
    template_name = 'Boletos/lista_bancos.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        logos_dir = os.path.join(base_dir, 'Logos')
        variation = self.request.GET.get('var', 'Colorido')
        tipo = (self.request.GET.get('tipo') or '').lower()
        dir_full = os.path.join(logos_dir, variation)
        bancos = []
        try:
            for f in os.listdir(dir_full):
                if f.lower().endswith('.bmp'):
                    codigo = os.path.splitext(f)[0]
                    item = {
                        'codigo': codigo,
                        'logo_path': os.path.join('boletos', 'Logos', variation, f),
                        'variation': variation,
                    }
                    # Filtro por tipo: exemplo 'caixa' => apenas 104
                    if tipo == 'caixa' and codigo != '104':
                        continue
                    bancos.append(item)
        except Exception:
            pass
        ctx['bancos'] = sorted(bancos, key=lambda x: x['codigo'])
        ctx['variation'] = variation
        ctx['tipo'] = tipo
        ctx['slug'] = self.kwargs.get('slug')
        return ctx
    
    def get_queryset(self):
        bancos = Entidades.objects.filter(enti_tipo_enti__isnull=False, enti_tien = 'B')
        
        return bancos
       
    
class BancoConfigCreateView(TemplateView):
    template_name = 'Boletos/banco_config_form.html'
    context_object_name = 'entidade'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = BancoConfigForm()
        ctx['slug'] = self.kwargs.get('slug')
        ctx['CNAB_CHOICES'] = CNAB_CHOICES
        return ctx

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request) or 'default'
        form = BancoConfigForm(request.POST)
        if form.is_valid():
            empresa = (
                self.request.session.get('empresa_id')
                or self.request.headers.get('X-Empresa')
                or self.request.POST.get('empresa')
                or self.request.GET.get('empresa')
            )
            try:
                if isinstance(empresa, str) and empresa.isdigit():
                    empresa = int(empresa)
            except Exception:
                pass
            if not empresa:
                return JsonResponse({'ok': False, 'erro': 'empresa_obrigatoria'}, status=400)
            obj = form.save(commit=False)
            if not getattr(obj, 'enti_tien', None):
                obj.enti_tien = 'B'
            obj.enti_empr = empresa
            obj.save(using=banco)
            
            return JsonResponse({'ok': True, 'enti_clie': obj.enti_clie, 'enti_banc': obj.enti_banc})
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    

class BancoConfigListView(ListView):
    template_name = 'Boletos/banco_config_list.html'
    context_object_name = 'entidades'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = self.request.session.get('empresa_id')
        qs = Entidades.objects.using(banco).filter(enti_empr=empresa, enti_tien__in=['B']).order_by('enti_nome')        
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.kwargs.get('slug')
        ctx['tipo'] = (self.request.GET.get('tipo') or '').lower()
        return ctx


class BancoConfigUpdateView(UpdateView):
    template_name = 'Boletos/banco_config_form.html'
    form_class = BancoConfigForm
    context_object_name = 'entidade'

    def get_object(self, queryset=None):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = (
            self.request.session.get('empresa_id')
            or self.request.headers.get('X-Empresa')
            or self.request.GET.get('empresa')
        )
        pk = self.kwargs.get('enti_clie')
        try:
            if isinstance(empresa, str) and empresa.isdigit():
                empresa = int(empresa)
        except Exception:
            empresa = None
        try:
            if isinstance(pk, str) and pk.isdigit():
                pk = int(pk)
        except Exception:
            pass
        qs = Entidades.objects.using(banco)
        if empresa:
            qs = qs.filter(enti_empr=empresa)
        return qs.filter(enti_clie=pk).first()

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        try:
            cfg = {
                'codigo_banco': str(self.request.POST.get('codigo_banco') or ''),
                'agencia': self.request.POST.get('agencia'),
                'conta': self.request.POST.get('conta'),
                'dv': self.request.POST.get('dv'),
                'carteira': self.request.POST.get('carteira'),
            }
            cx = validate_caixa_config(cfg)
            if not cx['ok']:
                return JsonResponse({'ok': False, 'erro': 'configuracao_caixa_invalida', 'detalhes': cx['errors']}, status=400)
        except Exception:
            pass
        obj = form.save(using=banco)
        return JsonResponse({'ok': True, 'enti_clie': obj.enti_clie, 'enti_banc': obj.enti_banc})

    def get_success_url(self):
        return reverse_lazy('banco_config_list', kwargs={'slug': self.kwargs.get('slug')})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.kwargs.get('slug')
        ctx['CNAB_CHOICES'] = CNAB_CHOICES
        return ctx
