# Configurações do Celery para o projeto mobile-sps
# Este arquivo centraliza todas as configurações de tasks agendadas

from celery.schedules import crontab
from datetime import timedelta

# Configurações básicas do Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Ajuste conforme sua configuração
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Araguaina'

# Configurações de performance
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Configurações de timeout
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutos
CELERY_TASK_TIME_LIMIT = 600  # 10 minutos

# Schedule otimizado para notificações - DESABILITADO
# As notificações agora são geradas SOB DEMANDA via endpoint /gerar-badge/
CELERY_BEAT_SCHEDULE = {
    # NOTIFICAÇÕES DESABILITADAS - Agora são sob demanda
    # 'notificacoes-diarias': {
    #     'task': 'notificacoes.tasks.enviar_notificacoes_diarias',
    #     'schedule': crontab(hour=8, minute=0),  # 08:00 da manhã
    #     'options': {
    #         'expires': 3600,  # Expira em 1 hora se não executar
    #     }
    # },
    
    # Limpeza de notificações antigas - semanal
    'limpeza-notificacoes': {
        'task': 'notificacoes.tasks.limpar_notificacoes_antigas',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Segunda-feira às 02:00
        'kwargs': {
            'dias_manter': 30,
            'apenas_lidas': True
        },
        'options': {
            'expires': 7200,  # Expira em 2 horas se não executar
        }
    },
    
    # Limpeza completa mensal (incluindo não lidas muito antigas)
    'limpeza-completa-mensal': {
        'task': 'notificacoes.tasks.limpar_notificacoes_antigas',
        'schedule': crontab(hour=3, minute=0, day_of_month=1),  # 1º do mês às 03:00
        'kwargs': {
            'dias_manter': 90,
            'apenas_lidas': False
        },
        'options': {
            'expires': 7200,
        }
    },
}

# Configurações de roteamento de tasks
CELERY_TASK_ROUTES = {
    'notificacoes.tasks.*': {'queue': 'notificacoes'},
    'auditoria.tasks.*': {'queue': 'auditoria'},
}

# Configurações de filas
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'notificacoes': {
        'exchange': 'notificacoes',
        'routing_key': 'notificacoes',
    },
    'auditoria': {
        'exchange': 'auditoria',
        'routing_key': 'auditoria',
    },
}

# Configurações de monitoramento
CELERY_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Configurações de retry
CELERY_TASK_ANNOTATIONS = {
    'notificacoes.tasks.enviar_notificacoes_diarias': {
        'rate_limit': '1/m',  # Máximo 1 por minuto
        'max_retries': 3,
        'default_retry_delay': 300,  # 5 minutos entre tentativas
    },
    'notificacoes.tasks.limpar_notificacoes_antigas': {
        'rate_limit': '1/h',  # Máximo 1 por hora
        'max_retries': 2,
        'default_retry_delay': 600,  # 10 minutos entre tentativas
    },
}

# Configurações de logging para Celery
CELERY_WORKER_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
CELERY_WORKER_TASK_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Configurações de segurança
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_IGNORE_RESULT = False
CELERY_RESULT_EXPIRES = 3600  # Resultados expiram em 1 hora

# Configurações específicas para desenvolvimento
import os
if os.environ.get('DEBUG', 'False').lower() == 'true':
    # Em desenvolvimento, executar tasks imediatamente
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    
    # Schedule mais frequente para testes
    CELERY_BEAT_SCHEDULE['notificacoes-diarias']['schedule'] = crontab(minute='*/30')  # A cada 30 min