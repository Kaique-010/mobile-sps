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
        context['empresa_id'] = self.empresa_id
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
        db_alias = getattr(request, 'db_alias', None)
        qs = Centrodecustos.objects.using(db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cecu_empr=int(self.empresa_id))
        base_unit = 10 ** Centrodecustos._mask_digits()
        sinteticos_sem_filho_sintetico = []
        for c in qs.filter(cecu_anal='S')[:2000]:
            faixa_min = int(c.cecu_redu) * base_unit + 1
            faixa_max = int(c.cecu_redu) * base_unit + (base_unit - 1)
            tem_sintetico = qs.filter(cecu_niv1=c.cecu_redu, cecu_anal='S', cecu_redu__gte=faixa_min, cecu_redu__lte=faixa_max).exists()
            if not tem_sintetico:
                sinteticos_sem_filho_sintetico.append(c)
        context['alert_sinteticos_sem_filho'] = sinteticos_sem_filho_sintetico
        context['mask_digits'] = Centrodecustos._mask_digits()
        context['mask_levels'] = Centrodecustos._mask_levels()
        return context


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


class CentrodeCustosCreateView(DBAndSlugMixin, CreateView):
    template_name = 'CentrodeCustos/centrodecusto_form.html'
    form_class = CentrodecustosForm
    model = Centrodecustos

    def get_form_kwargs(self):
        """Passa empresa_id para o formulário"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa_id'] = self.empresa_id
        return kwargs

    def get_context_data(self, **kwargs):
        """Adiciona dados de configuração ao contexto"""
        context = super().get_context_data(**kwargs)
        context['mask_digits'] = Centrodecustos._mask_digits()
        context['mask_levels'] = Centrodecustos._mask_levels()
        return context

    def form_valid(self, form):
        db_alias = getattr(self.request, 'db_alias', None)
        obj = form.save(commit=False)
        obj.cecu_empr = int(self.empresa_id or obj.cecu_empr or 0)
        try:
            obj.save(using=db_alias)
            self.object = obj
            messages.success(self.request, 'Centro de custos criado com sucesso.')
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            form.add_error(None, f'Erro ao criar centro de custos: {str(e)}')
            return self.form_invalid(form)

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
        """Passa empresa_id para o formulário"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa_id'] = self.empresa_id
        return kwargs

    def get_context_data(self, **kwargs):
        """Adiciona dados de configuração ao contexto"""
        context = super().get_context_data(**kwargs)
        context['mask_digits'] = Centrodecustos._mask_digits()
        context['mask_levels'] = Centrodecustos._mask_levels()
        return context

    def form_valid(self, form):
        db_alias = getattr(self.request, 'db_alias', None)
        obj = form.save(commit=False)
        obj.cecu_empr = int(self.empresa_id or obj.cecu_empr or 0)
        try:
            obj.save(using=db_alias)
            self.object = obj
            messages.success(self.request, 'Centro de custos atualizado com sucesso.')
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            form.add_error(None, f'Erro ao atualizar centro de custos: {str(e)}')
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('centrosdecustos:lista', kwargs={'slug': self.slug})


class ProximoCodigoCentrodeCustosView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias', None)
        parent = request.GET.get('cecu_niv1') or request.GET.get('parent')
        try:
            base_unit = 10 ** Centrodecustos._mask_digits()
            if parent:
                parent = int(parent)
                base = parent * base_unit
                faixa_min = base + 1
                faixa_max = base + (base_unit - 1)
                existing = list(
                    Centrodecustos.objects.using(db_alias)
                    .filter(
                        cecu_empr=int(self.empresa_id),
                        cecu_niv1=parent,
                        cecu_redu__gte=faixa_min,
                        cecu_redu__lte=faixa_max,
                    )
                    .order_by('cecu_redu')
                    .values_list('cecu_redu', flat=True)
                )
                expected = faixa_min
                for code in existing:
                    code = int(code)
                    if code != expected:
                        break
                    expected += 1
                proximo = expected
            else:
                existing = list(
                    Centrodecustos.objects.using(db_alias)
                    .filter(cecu_empr=int(self.empresa_id), cecu_niv1__isnull=True)
                    .order_by('cecu_redu')
                    .values_list('cecu_redu', flat=True)
                )
                expected = 1
                for code in existing:
                    code = int(code)
                    if code != expected:
                        break
                    expected += 1
                proximo = expected
            return JsonResponse({'next': proximo})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class AutocompletePaiCentrodeCustosView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias', None)
        q = (request.GET.get('q') or '').strip()
        qs = Centrodecustos.objects.using(db_alias).filter(cecu_empr=int(self.empresa_id or 0))
        if q:
            if q.isdigit():
                try:
                    qs = qs.filter(cecu_redu=int(q))
                except Exception:
                    pass
            else:
                qs = qs.filter(cecu_nome__icontains=q)
        qs = qs.order_by('cecu_redu')[:20]
        data = [
            {
                'id': int(c.cecu_redu or 0),
                'text': f"{c.cecu_redu} - {c.cecu_nome or ''} ({'Sintética' if c.cecu_anal=='S' else 'Analítica'})",
                'tipo': c.cecu_anal or '',
            }
            for c in qs
        ]
        return JsonResponse({'results': data})
