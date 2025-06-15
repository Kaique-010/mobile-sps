from celery import shared_task
from .views import (
    NotificaEstoqueView,
    NotificaFinanceiroView,
    NotificaVendasView,
    NotificaResumoView
)
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import AnonymousUser

@shared_task
def enviar_notificacoes_diarias():
    """Task para enviar notificações diárias automaticamente"""
    factory = APIRequestFactory()
    
    # Criar request fake para as views
    request = factory.post('/')
    request.user = AnonymousUser()
    
    resultados = {}
    
    # Notificações de estoque
    try:
        view = NotificaEstoqueView()
        response = view.post(request)
        resultados['estoque'] = response.data
    except Exception as e:
        resultados['estoque'] = {'error': str(e)}
    
    # Notificações financeiras
    try:
        view = NotificaFinanceiroView()
        response = view.post(request)
        resultados['financeiro'] = response.data
    except Exception as e:
        resultados['financeiro'] = {'error': str(e)}
    
    # Notificações de vendas
    try:
        view = NotificaVendasView()
        response = view.post(request)
        resultados['vendas'] = response.data
    except Exception as e:
        resultados['vendas'] = {'error': str(e)}
    
    # Resumo diário
    try:
        view = NotificaResumoView()
        response = view.post(request)
        resultados['resumo'] = response.data
    except Exception as e:
        resultados['resumo'] = {'error': str(e)}
    
    return resultados

@shared_task
def limpar_notificacoes_antigas():
    """Remove notificações antigas (mais de 30 dias)"""
    from datetime import datetime, timedelta
    from .models import Notificacao
    
    data_limite = datetime.now() - timedelta(days=30)
    deletadas = Notificacao.objects.filter(data_criacao__lt=data_limite).delete()
    
    return f"Removidas {deletadas[0]} notificações antigas"