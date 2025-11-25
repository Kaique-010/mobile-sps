from django.views.generic import TemplateView, ListView
from django.http import JsonResponse
from django.db import IntegrityError
from core.registry import get_licenca_db_config
from ...models import Carteira
from ..forms.carteira_form import CarteiraForm

class CarteiraListView(ListView):
    template_name = 'Boletos/carteiras.html'
    context_object_name = 'carteiras'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')
        banco_codigo = self.request.GET.get('banco') or self.request.headers.get('X-Banco') or self.request.GET.get('codigo_banco')
        if not empresa or not banco_codigo:
            return Carteira.objects.none()
        qs = Carteira.objects.using(banco).filter(cart_empr=empresa, cart_banc=banco_codigo)
        if filial:
            qs = qs.filter(cart_fili=filial)
        return qs.order_by('cart_codi')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.kwargs.get('slug')
        ctx['banco_codigo'] = self.request.GET.get('banco') or ''
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')
        banco_codigo = ctx['banco_codigo']
        ctx['form'] = CarteiraForm(database=banco, empresa_id=empresa, filial_id=filial, banco_codigo=banco_codigo)
        return ctx

class CarteiraCreateView(TemplateView):
    template_name = 'Boletos/carteiras.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        banco_codigo = self.request.GET.get('banco') or self.request.headers.get('X-Banco') or self.request.GET.get('codigo_banco')
        ctx['form'] = CarteiraForm(database=banco, empresa_id=empresa, banco_codigo=banco_codigo)
        ctx['slug'] = self.kwargs.get('slug')
        return ctx

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.POST.get('empresa') or request.GET.get('empresa')
        filial = request.session.get('filial_id') or request.headers.get('X-Filial') or request.POST.get('filial') or request.GET.get('filial')
        banco_codigo = request.POST.get('banco') or request.headers.get('X-Banco') or request.POST.get('codigo_banco')
        try:
            if isinstance(empresa, str) and empresa.isdigit():
                empresa = int(empresa)
            if isinstance(filial, str) and filial.isdigit():
                filial = int(filial)
        except Exception:
            pass
        if not empresa:
            return JsonResponse({'ok': False, 'erro': 'empresa_obrigatoria'}, status=400)
        form = CarteiraForm(request.POST, database=banco, empresa_id=empresa, filial_id=filial, banco_codigo=banco_codigo)
        if form.is_valid():
            try:
                obj = form.save()
            except Exception as e:
                return JsonResponse({'ok': False, 'errors': {'__all__': [str(e)]}}, status=400)
            try:
                data = obj.as_dict()
            except Exception:
                data = {
                    'cart_empr': getattr(obj, 'cart_empr', empresa),
                    'cart_banc': getattr(obj, 'cart_banc', banco_codigo),
                    'cart_codi': getattr(obj, 'cart_codi', None),
                    'cart_nome': getattr(obj, 'cart_nome', None),
                }
            return JsonResponse({'ok': True, 'carteira': data})
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

class CarteiraUpdateView(TemplateView):
    template_name = 'Boletos/carteiras.html'

    def get_object(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')
        banco_codigo = self.request.GET.get('banco') or self.request.headers.get('X-Banco')
        codigo = self.kwargs.get('codigo')
        qs = Carteira.objects.using(banco).filter(cart_empr=empresa, cart_banc=banco_codigo, cart_codi=codigo)
        if filial:
            qs = qs.filter(cart_fili=filial)
        return qs.first()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.get_object()
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')
        banco_codigo = (obj.cart_banc if obj else (self.request.GET.get('banco') or ''))
        ctx['form'] = CarteiraForm(instance=obj, database=banco, empresa_id=empresa, filial_id=filial, banco_codigo=banco_codigo)
        ctx['slug'] = self.kwargs.get('slug')
        return ctx

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.POST.get('empresa') or request.GET.get('empresa')
        filial = request.session.get('filial_id') or request.headers.get('X-Filial') or request.POST.get('filial') or request.GET.get('filial')
        banco_codigo = request.POST.get('banco') or request.headers.get('X-Banco') or request.POST.get('codigo_banco')
        try:
            if isinstance(empresa, str) and empresa.isdigit():
                empresa = int(empresa)
            if isinstance(filial, str) and filial.isdigit():
                filial = int(filial)
        except Exception:
            pass
        codigo_url = self.kwargs.get('codigo')
        obj_qs = Carteira.objects.using(banco).filter(cart_empr=empresa, cart_banc=banco_codigo, cart_codi=codigo_url)
        if filial:
            obj_qs = obj_qs.filter(cart_fili=filial)
        obj = obj_qs.first()
        if not obj:
            return JsonResponse({'ok': False, 'detail': 'Carteira não encontrada para edição'}, status=404)
        form = CarteiraForm(request.POST, instance=obj, database=banco, empresa_id=empresa, filial_id=filial, banco_codigo=banco_codigo)
        if form.is_valid():
            try:
                obj = form.save()
                return JsonResponse({'ok': True, 'carteira': obj.as_dict()})
            except IntegrityError:
                return JsonResponse({'ok': False, 'errors': {'__all__': ['Falha ao atualizar carteira.']}})
            except Exception as e:
                return JsonResponse({'ok': False, 'errors': {'__all__': [str(e)]}})
        return JsonResponse({'ok': False, 'errors': form.errors})

class CarteiraLookupView(TemplateView):
    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = request.session.get('empresa_id')
        filial = request.session.get('filial_id')
        banco_codigo = request.GET.get('banco') or request.headers.get('X-Banco') or request.GET.get('codigo_banco')
        codigo = request.GET.get('cart_codi')
        if not (empresa and banco_codigo and codigo):
            return JsonResponse({'ok': False, 'detail': 'Parâmetros insuficientes'}, status=400)
        obj = Carteira.lookup(banco_codigo, empresa, codigo, filial=filial, using=banco)
        if not obj:
            return JsonResponse({'ok': False, 'detail': 'Não encontrado'}, status=404)
        return JsonResponse({'ok': True, 'carteira': obj.as_dict()})

class CarteiraNextCodeView(TemplateView):
    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = request.session.get('empresa_id')
        filial = request.session.get('filial_id')
        banco_codigo = request.GET.get('banco') or request.headers.get('X-Banco') or request.GET.get('codigo_banco')
        if not (empresa and banco_codigo):
            return JsonResponse({'ok': False, 'detail': 'Parâmetros insuficientes'}, status=400)
        proximo = Carteira.next_code(banco_codigo, empresa, filial=filial, using=banco)
        return JsonResponse({'ok': True, 'proximo': proximo})
