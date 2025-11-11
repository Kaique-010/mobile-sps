from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Centrodecustos
from .forms import CentrodecustosForm
from core.utils import get_licenca_db_config


class DBAndSlugMixin:
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        db_alias = get_licenca_db_config(request)
        setattr(request, 'db_alias', db_alias)
        self.empresa_id = (
            request.session.get('empresa_id')
            or request.headers.get('X-Empresa')
            or request.GET.get('cecu_empr')
        )
        self.slug = kwargs.get(self.slug_url_kwarg)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = getattr(self, 'slug', None)
        context['current_year'] = timezone.now().year
        return context


class CentrodeCustosListView(DBAndSlugMixin, ListView):
    template_name = 'CentrodeCustos/centrosdecustos.html'
    context_object_name = 'centros'
    paginate_by = 20

    def get_queryset(self):
        request = self.request
        db_alias = getattr(request, 'db_alias', None)
        qs = Centrodecustos.objects.using(db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cecu_empr=int(self.empresa_id))
        # Filtros
        nome = request.GET.get('cecu_nome', '')
        codigo = request.GET.get('cecu_redu', '')
        if nome:
            qs = qs.filter(cecu_nome__icontains=nome)
        if codigo:
            try:
                qs = qs.filter(cecu_redu=int(codigo))
            except (ValueError, TypeError):
                pass
        return qs.order_by('cecu_empr', '-cecu_redu')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        context['cecu_nome'] = request.GET.get('cecu_nome', '')
        context['cecu_redu'] = request.GET.get('cecu_redu', '')
        return context


class CentrodeCustosCreateView(DBAndSlugMixin, CreateView):
    template_name = 'CentrodeCustos/centrodecusto_form.html'
    form_class = CentrodecustosForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        return reverse_lazy('centrosdecustos:lista', kwargs={'slug': self.slug})


class CentrodeCustosUpdateView(DBAndSlugMixin, UpdateView):
    template_name = 'CentrodeCustos/centrodecusto_form.html'
    form_class = CentrodecustosForm
    model = Centrodecustos
    pk_url_kwarg = 'cecu_redu'

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', None)
        qs = Centrodecustos.objects.using(db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cecu_empr=int(self.empresa_id))
        return qs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        return reverse_lazy('centrosdecustos:lista', kwargs={'slug': self.slug})


class CentrodeCustosDeleteView(DBAndSlugMixin, DeleteView):
    template_name = 'CentrodeCustos/centrodecusto_confirm_delete.html'
    model = Centrodecustos
    pk_url_kwarg = 'cecu_redu'

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', None)
        qs = Centrodecustos.objects.using(db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cecu_empr=int(self.empresa_id))
        return qs

    def delete(self, request, *args, **kwargs):
        try:
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {e}')
            return reverse_lazy('centrosdecustos:lista', kwargs={'slug': self.slug})

    def get_success_url(self):
        messages.success(self.request, 'Centro de custo excluído com sucesso.')
        return reverse_lazy('centrosdecustos:lista', kwargs={'slug': self.slug})


class ExportarCentrodeCustosView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias', None)
        nome = request.GET.get('cecu_nome', '')
        codigo = request.GET.get('cecu_redu', '')

        queryset = Centrodecustos.objects.using(db_alias).all().order_by('cecu_empr', 'cecu_redu')
        if nome:
            queryset = queryset.filter(cecu_nome__icontains=nome)
        if codigo:
            try:
                queryset = queryset.filter(cecu_redu=int(codigo))
            except (ValueError, TypeError):
                pass

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename=centrosdecustos.csv'

        import csv
        writer = csv.writer(response)
        writer.writerow(['Empresa', 'Código', 'Nome', 'Nível', 'Pai', 'Analítico/Sintético'])

        for c in queryset:
            writer.writerow([
                c.cecu_empr or '',
                c.cecu_redu or '',
                c.cecu_nome or '',
                c.cecu_nive or '',
                c.cecu_niv1 or '',
                c.cecu_anal or '',
            ])

        return response


class ProximoCodigoCentrodeCustosView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias', None)
        empresa_param = request.GET.get('empresa')
        print(f"Empresa param: {empresa_param}")
        empresa_id = int(empresa_param) if empresa_param else (int(self.empresa_id) if self.empresa_id else None)
        print(f"Empresa ID: {empresa_id}")
        parent = request.GET.get('parent')

        def _next_root_code():
            qs = Centrodecustos.objects.using(db_alias).filter(cecu_empr=empresa_id)
            last = qs.order_by('-cecu_redu').first()
            return (int(last.cecu_redu) + 1) if last and last.cecu_redu is not None else 1

        def _next_child_code(parent_code: int):
            base = int(parent_code) * 1000
            faixa_min = base + 1
            faixa_max = base + 999
            qs = Centrodecustos.objects.using(db_alias).filter(
                cecu_empr=empresa_id,
                cecu_niv1=parent_code,
                cecu_redu__gte=faixa_min,
                cecu_redu__lte=faixa_max,
            )
            last = qs.order_by('-cecu_redu').first()
            return (int(last.cecu_redu) + 1) if last and last.cecu_redu is not None else faixa_min

        try:
            if not empresa_id:
                return JsonResponse({'error': 'Empresa não definida'}, status=400)
            if parent:
                parent_code = int(parent)
                parent_obj = Centrodecustos.objects.using(db_alias).filter(cecu_empr=empresa_id, cecu_redu=parent_code).first()
                if not parent_obj:
                    return JsonResponse({'error': 'Pai não encontrado'}, status=404)
                code = _next_child_code(parent_code)
                level = (parent_obj.cecu_nive or 1) + 1
                tipo = 'A'
            else:
                code = _next_root_code()
                level = 1
                tipo = 'A'
            return JsonResponse({'code': code, 'level': level, 'tipo': tipo})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)