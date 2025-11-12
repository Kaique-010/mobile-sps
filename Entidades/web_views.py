from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import Http404, HttpResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from urllib.parse import quote_plus

from .models import Entidades
from .forms import EntidadesForm
from core.utils import get_licenca_db_config


class DBAndSlugMixin:
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        db_alias = get_licenca_db_config(request)
        setattr(request, 'db_alias', db_alias)
        # Capturar empresa/filial priorizando sessão; fallback para headers e querystring
        self.empresa_id = (
            request.session.get('empresa_id')
            or request.headers.get('X-Empresa')
            or request.GET.get('enti_empr')
        )
        self.filial_id = (
            request.session.get('filial_id')
            or request.headers.get('X-Filial')
            or request.GET.get('enti_fili')
        )
        self.slug = kwargs.get(self.slug_url_kwarg)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = getattr(self, 'slug', None)
        context['current_year'] = timezone.now().year
        return context


class EntidadeListView(DBAndSlugMixin, ListView):
    template_name = 'Entidades/entidades.html'
    context_object_name = 'entidades'
    paginate_by = 20

    def get_queryset(self):
        request = self.request
        db_alias = getattr(request, 'db_alias', None)
        qs = Entidades.objects.using(db_alias).all()
        # Filtrar por empresa quando disponível para evitar duplicidades
        if self.empresa_id:
            qs = qs.filter(enti_empr=int(self.empresa_id))
        qs = qs.order_by('enti_empr', 'enti_nome')
        nome = request.GET.get('enti_nome', '')
        id_cliente = request.GET.get('enti_clie', '')
        if nome:
            qs = qs.filter(enti_nome__icontains=nome)
        if id_cliente:
            try:
                qs = qs.filter(enti_clie=int(id_cliente))
            except (ValueError, TypeError):
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        nome = request.GET.get('enti_nome', '')
        id_cliente = request.GET.get('enti_clie', '')
        context['nome'] = nome
        context['id_cliente'] = id_cliente
        # Preservar filtros na paginação
        extra_parts = []
        if nome:
            extra_parts.append('&enti_nome=' + quote_plus(nome))
        if id_cliente:
            extra_parts.append('&enti_clie=' + quote_plus(id_cliente))
        context['extra_query'] = ''.join(extra_parts)
        return context


class EntidadeCreateView(DBAndSlugMixin, CreateView):
    template_name = 'Entidades/entidade_form.html'
    form_class = EntidadesForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        return reverse_lazy('entidades_web', kwargs={'slug': self.slug})


class EntidadeUpdateView(DBAndSlugMixin, UpdateView):
    template_name = 'Entidades/entidade_form.html'
    form_class = EntidadesForm
    model = Entidades
    pk_url_kwarg = 'enti_clie'

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', None)
        qs = Entidades.objects.using(db_alias).all()
        if self.empresa_id:
            qs = qs.filter(enti_empr=int(self.empresa_id))
        return qs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        return reverse_lazy('entidades_web', kwargs={'slug': self.slug})


class EntidadeDeleteView(DBAndSlugMixin, DeleteView):
    template_name = 'Entidades/entidade_confirm_delete.html'
    model = Entidades
    pk_url_kwarg = 'enti_clie'

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', None)
        qs = Entidades.objects.using(db_alias).all()
        if self.empresa_id:
            qs = qs.filter(enti_empr=int(self.empresa_id))
        return qs

    def delete(self, request, *args, **kwargs):
        try:
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {e}')
            return redirect('entidades_web', slug=self.slug)

    def get_success_url(self):
        messages.success(self.request, 'Entidade excluída com sucesso.')
        return reverse_lazy('entidades_web', kwargs={'slug': self.slug})


class ExportarEntidadesView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias', None)
        nome = request.GET.get('enti_nome', '')
        id_cliente = request.GET.get('enti_clie', '')

        queryset = Entidades.objects.using(db_alias).all().order_by('enti_empr', 'enti_nome')
        if nome:
            queryset = queryset.filter(enti_nome__icontains=nome)
        if id_cliente:
            try:
                queryset = queryset.filter(enti_clie=int(id_cliente))
            except (ValueError, TypeError):
                pass

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename=entidades.csv'

        import csv
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Nome', 'Classificação', 'CPF', 'CNPJ', 'Cidade', 'Estado', 'Telefone', 'Celular', 'Email'
        ])

        for e in queryset:
            writer.writerow([
                e.enti_clie or '',
                e.enti_nome or '',
                e.enti_tipo_enti or '',
                e.enti_cpf or '',
                e.enti_cnpj or '',
                e.enti_cida or '',
                e.enti_esta or '',
                e.enti_fone or '',
                e.enti_celu or '',
                e.enti_emai or '',
            ])

        return response