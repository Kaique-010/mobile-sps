from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import LogAcao
from core.middleware import get_licenca_slug
import threading
import logging
import json

logger = logging.getLogger(__name__)

# Thread local storage para armazenar dados temporários
_thread_locals = threading.local()

User = get_user_model()

def get_current_user():
    """Obtém o usuário atual do contexto da thread"""
    return getattr(_thread_locals, 'user', None)

def set_current_user(user):
    """Define o usuário atual no contexto da thread"""
    _thread_locals.user = user

def get_current_request():
    """Obtém a requisição atual do contexto da thread"""
    return getattr(_thread_locals, 'request', None)

def set_current_request(request):
    """Define a requisição atual no contexto da thread"""
    _thread_locals.request = request

class AuditoriaSignalMiddleware:
    """Middleware para capturar usuário e requisição nos signals"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        set_current_request(request)
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        
        response = self.get_response(request)
        
        # Limpar contexto após a requisição
        set_current_request(None)
        set_current_user(None)
        
        return response

@receiver(pre_save)
def capturar_dados_antes_salvar(sender, instance, **kwargs):
    """Captura dados antes de salvar para detectar alterações"""
    # Ignorar o próprio modelo de auditoria
    if sender == LogAcao:
        return
    
    # Só capturar se é uma atualização (objeto já existe)
    if instance.pk:
        try:
            db_alias = getattr(getattr(instance, '_state', None), 'db', None)
            manager = sender.objects if not db_alias else sender.objects.using(db_alias)
            dados_anteriores = manager.get(pk=instance.pk)
            # Armazenar no contexto da thread
            if not hasattr(_thread_locals, 'dados_antes'):
                _thread_locals.dados_antes = {}
            _thread_locals.dados_antes[f"{sender.__name__}_{instance.pk}"] = model_to_dict(dados_anteriores)
        except (sender.DoesNotExist, sender.MultipleObjectsReturned):
            # Ignorar se não existe ou se há múltiplos objetos com a mesma PK
            # Isso pode acontecer em modelos com chaves primárias compostas mal definidas
            pass

@receiver(post_save)
def log_criacao_atualizacao(sender, instance, created, **kwargs):
    """Registra logs de criação e atualização"""
    # Ignorar o próprio modelo de auditoria
    if sender == LogAcao:
        return
    
    try:
        user = get_current_user()
        request = get_current_request()
        
        # Se não há usuário ou requisição, pode ser uma operação interna
        if not user or not request:
            logger.debug(f'Signal ignorado - sem contexto de usuário/requisição para {sender.__name__} ID {instance.pk}')
            return
        
        # Obter licença
        licenca_slug = get_licenca_slug()
        db_alias = getattr(getattr(instance, '_state', None), 'db', None) or licenca_slug or 'default'
        if not licenca_slug:
            logger.debug(f'Signal ignorado - sem licença para {sender.__name__} ID {instance.pk}')
            return
        
        dados_depois = model_to_dict(instance)
        dados_antes = None
        campos_alterados = None
        tipo_acao = 'POST' if created else 'PUT'
        
        if not created:
            # É uma atualização, tentar obter dados anteriores
            chave_dados = f"{sender.__name__}_{instance.pk}"
            if hasattr(_thread_locals, 'dados_antes') and chave_dados in _thread_locals.dados_antes:
                dados_antes = _thread_locals.dados_antes[chave_dados]
                campos_alterados = comparar_dados_signal(dados_antes, dados_depois)
                # Limpar dados após uso
                del _thread_locals.dados_antes[chave_dados]
        
        # Extrair empresa da URL se disponível
        empresa = None
        if request and hasattr(request, 'path'):
            path_parts = request.path.strip('/').split('/')
            empresa = path_parts[1] if len(path_parts) > 1 else None
        
        # Criar log
        LogAcao.objects.using(db_alias).create(
            usuario=user,
            data_hora=timezone.now(),
            tipo_acao=tipo_acao,
            url=request.path if request else f'/db/{sender.__name__.lower()}/{instance.pk}/',
            ip=request.META.get('REMOTE_ADDR') if request else None,
            navegador=request.META.get('HTTP_USER_AGENT', '') if request else 'Sistema Interno',
            dados=None,  # Dados da requisição não disponíveis nos signals
            dados_antes=json.dumps(dados_antes, ensure_ascii=False) if dados_antes is not None else None,
            dados_depois=json.dumps(dados_depois, ensure_ascii=False) if dados_depois is not None else None,
            campos_alterados=json.dumps(campos_alterados, ensure_ascii=False) if campos_alterados is not None else None,
            objeto_id=str(instance.pk),
            modelo=sender.__name__,
            empresa=empresa,
            licenca=licenca_slug
        )

        logger.info(f'Log signal criado: {tipo_acao} {sender.__name__} ID {instance.pk}')
        
    except Exception as e:
        logger.error(f'Erro ao criar log via signal: {str(e)}')
        logger.exception('Detalhes do erro:')

@receiver(post_delete)
def log_exclusao(sender, instance, **kwargs):
    """Registra logs de exclusão"""
    # Ignorar o próprio modelo de auditoria
    if sender == LogAcao:
        return
    
    try:
        user = get_current_user()
        request = get_current_request()
        
        # Se não há usuário ou requisição, pode ser uma operação interna
        if not user or not request:
            logger.debug(f'Signal de exclusão ignorado - sem contexto para {sender.__name__} ID {instance.pk}')
            return
        
        # Obter licença
        licenca_slug = get_licenca_slug()
        db_alias = getattr(getattr(instance, '_state', None), 'db', None) or licenca_slug or 'default'
        if not licenca_slug:
            logger.debug(f'Signal de exclusão ignorado - sem licença para {sender.__name__} ID {instance.pk}')
            return
        
        dados_antes = model_to_dict(instance)
        
        # Extrair empresa da URL se disponível
        empresa = None
        if request and hasattr(request, 'path'):
            path_parts = request.path.strip('/').split('/')
            empresa = path_parts[1] if len(path_parts) > 1 else None
        
        # Criar log
        LogAcao.objects.using(db_alias).create(
            usuario=user,
            data_hora=timezone.now(),
            tipo_acao='DELETE',
            url=request.path if request else f'/db/{sender.__name__.lower()}/{instance.pk}/',
            ip=request.META.get('REMOTE_ADDR') if request else None,
            navegador=request.META.get('HTTP_USER_AGENT', '') if request else 'Sistema Interno',
            dados=None,  # Dados da requisição não disponíveis nos signals
            dados_antes=json.dumps(dados_antes, ensure_ascii=False) if dados_antes is not None else None,
            dados_depois=None,  # Objeto foi excluído
            campos_alterados=None,
            objeto_id=str(instance.pk),
            modelo=sender.__name__,
            empresa=empresa,
            licenca=licenca_slug
        )

        logger.info(f'Log signal de exclusão criado: {sender.__name__} ID {instance.pk}')
        
    except Exception as e:
        logger.error(f'Erro ao criar log de exclusão via signal: {str(e)}')
        logger.exception('Detalhes do erro:')

def comparar_dados_signal(dados_antes, dados_depois):
    """Compara dois dicionários e retorna as diferenças (versão para signals)"""
    if not dados_antes or not dados_depois:
        return None
    
    alteracoes = {}
    
    # Verificar campos alterados
    for campo, valor_depois in dados_depois.items():
        valor_antes = dados_antes.get(campo)
        
        # Converter para string para comparação consistente
        str_antes = str(valor_antes) if valor_antes is not None else None
        str_depois = str(valor_depois) if valor_depois is not None else None
        
        if str_antes != str_depois:
            alteracoes[campo] = {
                'antes': valor_antes,
                'depois': valor_depois
            }
    
    # Verificar campos removidos
    for campo, valor_antes in dados_antes.items():
        if campo not in dados_depois:
            alteracoes[campo] = {
                'antes': valor_antes,
                'depois': None
            }
    
    return alteracoes if alteracoes else None
