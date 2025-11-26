from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView

from .models import Centrodecustos
from .forms import CentrodecustosForm
from core.utils import get_licenca_db_config
from .service import get_children, MASCARA


class DBAndSlugMixin:
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        db_alias = get_licenca_db_config(request)
        setattr(request, 'db_alias', db_alias)

        self.slug = kwargs.get(self.slug_url_kwarg)

        self.empresa_id = (
            request.session.get('empresa_id')
            or request.headers.get('X-Empresa')
            or request.GET.get('cecu_empr')
        )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.slug
        context['empresa_id'] = self.empresa_id
        context['current_year'] = timezone.now().year
        return context


class CentrodeCustosListView(DBAndSlugMixin, TemplateView):
    template_name = 'CentrodeCustos/centrosdecustos.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        empresa = int(self.empresa_id or 0)
        db_alias = getattr(self.request, 'db_alias', None)

        qs = Centrodecustos.objects.using(db_alias).filter(cecu_empr=empresa)

        ctx['roots'] = qs.filter(cecu_nive=1).order_by("cecu_expa")

        # Para filtros da lista
        nome = self.request.GET.get('cecu_nome', '')
        codigo = self.request.GET.get('cecu_redu', '')

        if nome:
            qs = qs.filter(cecu_nome__icontains=nome)
        if codigo:
            try:
                qs = qs.filter(cecu_redu=int(codigo))
            except ValueError:
                pass

        ctx['centros'] = qs.order_by("cecu_expa")[:3000]  # safe cap
        ctx['cecu_nome'] = nome
        ctx['cecu_redu'] = codigo
        ctx['empresa'] = empresa
        ctx['max_depth'] = len(MASCARA)

        return ctx

class CentrodeCustosDeleteView(DBAndSlugMixin, DeleteView):
    template_name = 'CentrodeCustos/centrodecusto_confirm_delete.html'
    model = Centrodecustos
    pk_url_kwarg = 'cecu_redu'

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias')
        empresa = int(self.empresa_id or 0)
        return Centrodecustos.objects.using(db_alias).filter(cecu_empr=empresa)

    def delete(self, request, *args, **kwargs):
        try:
            messages.success(request, "Centro de custos excluído com sucesso.")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f"Erro ao excluir: {e}")
            return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("centrosdecustos:lista", kwargs={"slug": self.slug})


class ExportarCentrodeCustosView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias')
        empresa = int(self.empresa_id or 0)

        qs = Centrodecustos.objects.using(db_alias).filter(cecu_empr=empresa).order_by("cecu_expa")

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename=centrosdecustos.csv'

        import csv
        writer = csv.writer(response)
        writer.writerow(['Empresa', 'Código', 'Nome', 'Nível', 'Tipo'])

        for c in qs:
            writer.writerow([
                c.cecu_empr,
                c.cecu_expa,
                c.cecu_nome,
                c.cecu_nive,
                c.cecu_anal
            ])

        return response


class CentrodeCustosCreateView(DBAndSlugMixin, CreateView):
    template_name = 'CentrodeCustos/centrodecusto_form.html'
    form_class = CentrodecustosForm
    model = Centrodecustos

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['empresa_id'] = self.empresa_id
        kwargs['db_alias'] = getattr(self.request, 'db_alias', None)
        return kwargs

    def get_initial(self):
        return {
            "parent": self.request.GET.get("parent", None)
        }

    def form_valid(self, form):
        db_alias = getattr(self.request, 'db_alias', None)
        try:
            obj = form.save(commit=False)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

        obj.cecu_empr = int(self.empresa_id or 0)

        try:
            obj.save(using=db_alias)
            messages.success(self.request, "Centro de custos criado com sucesso.")
        except Exception as e:
            form.add_error(None, f"Erro ao criar centro de custos: {e}")
            return self.form_invalid(form)

        self.object = obj
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("centrosdecustos:lista", kwargs={"slug": self.slug})

class CentrodeCustosUpdateView(DBAndSlugMixin, UpdateView):
    template_name = 'CentrodeCustos/centrodecusto_form.html'
    form_class = CentrodecustosForm
    model = Centrodecustos
    pk_url_kwarg = 'cecu_redu'

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', None)
        empresa = int(self.empresa_id or 0)
        return Centrodecustos.objects.using(db_alias).filter(cecu_empr=empresa)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['empresa_id'] = self.empresa_id
        kwargs['db_alias'] = getattr(self.request, 'db_alias', None)
        return kwargs

    def form_valid(self, form):
        db_alias = getattr(self.request, 'db_alias', None)
        try:
            obj = form.save(commit=False)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        obj.cecu_empr = int(self.empresa_id)
        try:
            obj.save(using=db_alias)
            messages.success(self.request, "Centro de custos atualizado.")
        except Exception as e:
            form.add_error(None, f"Erro ao atualizar: {e}")
            return self.form_invalid(form)
        self.object = obj
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("centrosdecustos:lista", kwargs={"slug": self.slug})





class AutocompletePaiCentrodeCustosView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias')
        empresa = int(self.empresa_id or 0)

        q = request.GET.get("q", "").strip()

        qs = Centrodecustos.objects.using(db_alias).filter(cecu_empr=empresa)

        if q:
            if q.isdigit():
                qs = qs.filter(cecu_redu=int(q))
            else:
                qs = qs.filter(cecu_nome__icontains=q)

        qs = qs.order_by("cecu_expa")[:20]

        data = [{
            "id": c.cecu_expa,
            "text": f"{c.cecu_expa} - {c.cecu_nome} ({'Sintética' if c.cecu_anal=='S' else 'Analítica'})",
            "tipo": c.cecu_anal,
        } for c in qs]

        return JsonResponse({"results": data})
