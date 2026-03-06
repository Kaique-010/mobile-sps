import logging
from django.shortcuts import render, redirect
from django.contrib import messages

logger = logging.getLogger(__name__)
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import Http404, HttpResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView
from Entidades.web_views import DBAndSlugMixin
from auditoria.models import LogAcao
from django.contrib.auth import get_user_model

class AuditoriaListView(DBAndSlugMixin, ListView):
    model = LogAcao
    template_name = 'Auditoria/auditoria_list.html'
    context_object_name = 'auditorias'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filtro por tipo de ação
        tipo = self.request.GET.get('tipo')
        if tipo:
            qs = qs.filter(tipo_acao=tipo)
            
        # Filtro por usuário
        usuario_id = self.request.GET.get('usuario')
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
            
        # Filtro por modelo
        modelo = self.request.GET.get('modelo')
        if modelo:
            qs = qs.filter(modelo=modelo)
        
        data_inicio = self.request.GET.get('data_inicio')
        if data_inicio:
            try:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                dt_inicio = dt_inicio - timedelta(days=1)
                qs = qs.filter(data_hora__gte=dt_inicio)
            except ValueError:
                pass
            
        data_fim = self.request.GET.get('data_fim')
        if data_fim:
            try:
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                dt_fim = dt_fim + timedelta(days=1)
                qs = qs.filter(data_hora__lte=dt_fim)
            except ValueError:
                pass
        

        # Excluir logs do próprio app de auditoria
        qs = qs.exclude(url__contains='/auditoria/')

        qs = qs.order_by('-data_hora')
        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.kwargs.get('slug')
        ctx['tipo_selecionado'] = self.request.GET.get('tipo')
        ctx['usuario_selecionado'] = self.request.GET.get('usuario')
        ctx['modelo_selecionado'] = self.request.GET.get('modelo')
        ctx['data_inicio'] = self.request.GET.get('data_inicio')
        ctx['data_fim'] = self.request.GET.get('data_fim')
        
        # Dados para os filtros
        ctx['tipos_acao'] = LogAcao.TIPO_ACAO_CHOICES
        ctx['usuarios'] = get_user_model().objects.all().order_by('usua_nome')
        ctx['modelos'] = LogAcao.objects.values_list('modelo', 'modelo').distinct().order_by('modelo')
        
        return ctx