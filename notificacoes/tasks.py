from celery import shared_task
from .views import NotificaTudoView
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import AnonymousUser
from core.utils import get_licenca_db_config
from Licencas.models import Licencas
import logging

logger = logging.getLogger(__name__)

@shared_task
def enviar_notificacoes_diarias(slug=None):
    """
    Task otimizada para enviar notificações diárias automaticamente
    Agora usa o sistema de controle de duplicatas
    """
    resultados = {}
    
    try:
        # Se não especificar slug, processa todas as licenças ativas
        if slug:
            slugs = [slug]
        else:
            slugs = Licencas.objects.filter(ativo=True).values_list('slug', flat=True)
        
        for licenca_slug in slugs:
            try:
                factory = APIRequestFactory()
                # Criar request com dados mínimos necessários
                request = factory.post('/', data={}, format='json')
                request.user = AnonymousUser()  # Será tratado pela view
                
                # Usar a view otimizada que já tem controle de duplicatas
                view = NotificaTudoView()
                response = view.post(request, slug=licenca_slug)
                
                resultados[licenca_slug] = {
                    'status': 'sucesso',
                    'dados': response.data
                }
                
                logger.info(f"Notificações processadas para {licenca_slug}: {response.data}")
                
            except Exception as e:
                resultados[licenca_slug] = {
                    'status': 'erro',
                    'erro': str(e)
                }
                logger.error(f"Erro ao processar notificações para {licenca_slug}: {str(e)}")
    
    except Exception as e:
        resultados['erro_geral'] = str(e)
        logger.error(f"Erro geral na task de notificações: {str(e)}")
    
    return resultados

@shared_task
def limpar_notificacoes_antigas(dias_manter=30, apenas_lidas=True):
    """
    Remove notificações antigas de todas as licenças
    Agora usa o sistema otimizado de limpeza
    """
    from datetime import datetime, timedelta
    from .models import Notificacao
    from Licencas.models import Licencas
    from django.utils import timezone
    
    resultados = {}
    total_removidas = 0
    
    try:
        # Processar todas as licenças ativas
        licencas = Licencas.objects.filter(ativo=True)
        
        for licenca in licencas:
            try:
                data_limite = timezone.now() - timedelta(days=dias_manter)
                
                filtros = {'data_criacao__lt': data_limite}
                if apenas_lidas:
                    filtros['lida'] = True
                
                # Contar antes de deletar
                count = Notificacao.objects.using(licenca.slug).filter(**filtros).count()
                
                # Deletar
                if count > 0:
                    Notificacao.objects.using(licenca.slug).filter(**filtros).delete()
                    total_removidas += count
                
                resultados[licenca.slug] = {
                    'removidas': count,
                    'criterio': f"{'Lidas' if apenas_lidas else 'Todas'} com mais de {dias_manter} dias"
                }
                
                logger.info(f"Limpeza {licenca.slug}: {count} notificações removidas")
                
            except Exception as e:
                resultados[licenca.slug] = {'erro': str(e)}
                logger.error(f"Erro na limpeza {licenca.slug}: {str(e)}")
    
    except Exception as e:
        resultados['erro_geral'] = str(e)
        logger.error(f"Erro geral na limpeza: {str(e)}")
    
    resultados['total_geral'] = total_removidas
    return resultados