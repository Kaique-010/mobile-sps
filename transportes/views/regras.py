from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.db import transaction

from core.utils import get_licenca_db_config
from transportes.models import RegraICMS
from transportes.forms.regras import RegraICMSForm
from django import forms


class RegraICMSListView(ListView):
    model = RegraICMS
    template_name = 'transportes/regras/regra_list.html'
    context_object_name = 'regras'
    ordering = ['uf_origem', 'uf_destino']

    def get_queryset(self):
        slug = get_licenca_db_config(self.request)
        return RegraICMS.objects.using(slug).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = get_licenca_db_config(self.request)
        return context

class RegraICMSCreateView(CreateView):
    model = RegraICMS
    form_class = RegraICMSForm
    template_name = 'transportes/regras/regra_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = get_licenca_db_config(self.request)
        return context
    
    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse_lazy('transportes:regra_list', kwargs={'slug': slug})

    def form_valid(self, form):
        slug = get_licenca_db_config(self.request)
        self.object = form.save(commit=False)
        self.object.save(using=slug)
        messages.success(self.request, "Regra criada com sucesso!")
        return HttpResponseRedirect(self.get_success_url())

class RegraICMSUpdateView(UpdateView):
    model = RegraICMS
    form_class = RegraICMSForm
    template_name = 'transportes/regras/regra_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self):
        slug = get_licenca_db_config(self.request)
        return RegraICMS.objects.using(slug).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = get_licenca_db_config(self.request)
        return context

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse_lazy('transportes:regra_list', kwargs={'slug': slug})
    
    def form_valid(self, form):
        slug = get_licenca_db_config(self.request)
        self.object = form.save(commit=False)
        self.object.save(using=slug)
        messages.success(self.request, "Regra atualizada com sucesso!")
        return HttpResponseRedirect(self.get_success_url())

class RegraICMSDeleteView(DeleteView):
    model = RegraICMS
    template_name = 'transportes/regras/regra_confirm_delete.html'
    
    def get_queryset(self):
        slug = get_licenca_db_config(self.request)
        return RegraICMS.objects.using(slug).all()

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse_lazy('transportes:regra_list', kwargs={'slug': slug})

    def delete(self, request, *args, **kwargs):
        slug = get_licenca_db_config(self.request)
        self.object = self.get_object()
        self.object.delete(using=slug)
        messages.success(self.request, "Regra excluída com sucesso!")
        return HttpResponseRedirect(self.get_success_url())
