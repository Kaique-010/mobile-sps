from ctypes import cast
from email.policy import default
from pathlib import Path
from decouple import config  
from django.utils.timezone import timedelta
import os


BASE_DIR = Path(__file__).resolve().parent.parent

# Variáveis de configuração gerais
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# Hosts permitidos
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# Configuração WSGI padrão (ASGI removido)

USE_LOCAL_DB = config('USE_LOCAL_DB', default=True, cast=bool)

# ============================================================================
# CONFIGURAÇÕES DE BANCO DE DADOS - OTIMIZADAS
# ============================================================================

if USE_LOCAL_DB:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('LOCAL_DB_NAME'),
            'USER': config('LOCAL_DB_USER'),
            'PASSWORD': config('LOCAL_DB_PASSWORD'),
            'HOST': config('LOCAL_DB_HOST'),
            'PORT': config('LOCAL_DB_PORT'),
            'OPTIONS': {
                'options': '-c timezone=America/Araguaina',
                'connect_timeout': 30,  # Aumentado de 10 para 30
                'application_name': 'mobile_sps',
            },
            'CONN_MAX_AGE': 600,  # 10 minutos (era 300 - aumentado)
            'CONN_HEALTH_CHECKS': True,
            'ATOMIC_REQUESTS': False,
            'AUTOCOMMIT': True,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('REMOTE_DB_NAME'),
            'USER': config('REMOTE_DB_USER'),
            'PASSWORD': config('REMOTE_DB_PASSWORD'),
            'HOST': config('REMOTE_DB_HOST'),
            'PORT': config('REMOTE_DB_PORT'),
            'OPTIONS': {
                'options': '-c timezone=America/Araguaina',
                'connect_timeout': 30,  # Aumentado de 10 para 30
                'application_name': 'mobile_sps',
                # Adicionar configurações de pool para estabilidade
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
            },
            'CONN_MAX_AGE': 600,  # 10 minutos
            'CONN_HEALTH_CHECKS': True,
            'ATOMIC_REQUESTS': False,
            'AUTOCOMMIT': True,
        }
    }


import logging
logger = logging.getLogger("django")
logger.warning("🧠 BASE USADA: %s", "LOCAL" if USE_LOCAL_DB else "REMOTA")


DATABASE_ROUTERS = ['core.db_router.LicencaDBRouter']

# Definir aplicativos instalados
INSTALLED_APPS = [
    'core',  # Adicionar core como app
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_filters',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    # 'channels',  # Removido para eliminar WebSocket
    #'sklearn',
    'Licencas',
    'Produtos',
    'Entidades',
    'Pedidos',
    'Orcamentos',
    'dashboards',
    'Entradas_Estoque',
    'Saidas_Estoque',
    'listacasamento',
    'implantacao',
    'CFOP',
    'contas_a_pagar',
    'contas_a_receber',
    'contratos', 
    'OrdemdeServico',
    'CaixaDiario',
    "O_S", 
    "auditoria",
    "notificacoes",
    "Sdk_recebimentos",
    "SpsComissoes",
    "EnvioCobranca",
    "DRE",
    #"Gerencial",
    "OrdemProducao",
    'parametros_admin',
    'mcp_agent_db',  
    'controledevisitas',
    'Pisos',
    'drf_spectacular',
    'coletaestoque',
    'Floresta',
    'Lancamentos_Bancarios',
    'Notas_Fiscais',
    'NotasDestinadas',
    'Assistente_Spart',
    'ParametrosSps',
    'Financeiro',
    'CentrodeCustos',
    'boletos',
    'onboarding',
    'series',
    'importador',
    'centraldeajuda',
    'osexterna',
    'licencas_web',
    'perfilweb',
    'controledePonto',
    'Agricola',
    'adiantamentos',
]

# Middleware
MIDDLEWARE = [
    'core.performance_middleware.PerformanceMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.LicencaMiddleware',
    'core.middleware_restore_auth.RestoreUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditoria.middleware.AuditoriaMiddleware',
    #'perfilweb.middleware.PerfilPermissionMiddleware',
]


# Configurações de CORS
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')

# Adicionar configurações específicas para headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-cnpj',
    'x-username', 
    'setor',
    'x-email',
    'x-cpf',
    'x-Docu',
    'x-Empresa',
    'x-EmpresaID',
    'x-Filial',
    'x-FilialID',
    'x-Entidade',
    'x-session-id',
    
]

CORS_ALLOW_CREDENTIALS = True
ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates_spsWeb',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.empresa_filial_names',
                'onboarding.context_processors.onboarding_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

AUTHENTICATION_BACKENDS = [
    'Licencas.backends.UserBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = 'Licencas.Usuarios'

# URLs de autenticação para redirecionar corretamente páginas protegidas (LoginRequired)
LOGIN_URL = '/web/login/'
LOGIN_REDIRECT_URL = '/web/home/'
LOGOUT_REDIRECT_URL = '/web/login/'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Araguaina'
USE_TZ = False
USE_I18N = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações do Django REST Framework com otimizações
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        #'Licencas.authentication.CustomJWTAuthentication',  # Autenticação customizada
        #'Entidades.authentication.EntidadeJWTAuthentication', 
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',        
        'rest_framework.parsers.FormParser',       
        'rest_framework.parsers.MultiPartParser',  
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,  # Otimizado para performance
    'MAX_PAGE_SIZE': 250,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


SIMPLE_JWT = {
    "USER_ID_FIELD": "usua_codi",
    "USER_ID_CLAIM": "usua_codi",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),        
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION", 
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'Mobile SPS API',
    'DESCRIPTION': 'Documentação da API para o sistema Mobile SPS',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'displayRequestDuration': True,
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'tryItOutEnabled': True,
    },
    'ENUM_NAME_OVERRIDES': {
        'PatchedMobileSpsUserRequestStatusEnum': 'MobileSpsUserRequestStatusEnum',
        'PatchedMobileSpsUserRequestTypeEnum': 'MobileSpsUserRequestTypeEnum',
        'ClientEnum': 'core.utils.ClientEnum',
    },
}

APPEND_SLASH = True

# Configurações de timeout para produção
GUNICORN_TIMEOUT = 120  # 2 minutos

# Configurações de logging consolidadas
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name}: {message}',
            'style': '{',
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['console'],
            'level': 'ERROR' if not DEBUG else 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'Orcamentos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'O_S': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        },
        'Entidades': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',  
            'propagate': False,
        },
        'Produtos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'Pedidos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'listacasamento.views': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        },
        'Pisos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        },
        'PedidosPisos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        },
        'Assistente_Spart': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        },
        'ItensPedidosPisos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        },
        'ControleDeVisitas': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        },
        'perfilweb.middleware': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        }
    },
}

# Desabilitar migrações para apps legados (tabelas já existem)
# Mantém apenas 'licencas_web' com migrações ativas
MIGRATION_MODULES = {
    'CaixaDiario': None,
    'Entidades': None,
    'Entradas_Estoque': None,
    'EnvioCobranca': None,
    'Licencas': None,
    'O_S': None,
    'OrdemProducao': None,
    'OrdemdeServico': None,
    'Pedidos': None,
    'Produtos': None,
    'Saidas_Estoque': None,
    'Sdk_recebimentos': None,
    'SpsComissoes': None,
    'auditoria': None,
    'centraldeajuda': None,
    'coletaestoque': None,
    'contas_a_pagar': None,
    'contas_a_receber': None,
    'contratos': None,
    'controledevisitas': None,
    'dashboards': None,
    'implantacao': None,
    'listacasamento': None,
    'notificacoes': None,
    'onboarding': None,
    'parametros_admin': None,
}

# Configurações de E-mail
EMAIL_BACKEND = config('EMAIL_BACKEND')
EMAIL_HOST = config('EMAIL_HOST') 
EMAIL_PORT = int(config('EMAIL_PORT'))
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# Patch para SMTP
CFOP_SUGGESTION_API_URL = config('CFOP_SUGGESTION_API_URL', default='')
import smtplib

orig_starttls = smtplib.SMTP.starttls

def starttls_patch(self, *args, **kwargs):
    # Remove keyfile e certfile se passados para evitar erro
    if 'keyfile' in kwargs:
        del kwargs['keyfile']
    if 'certfile' in kwargs:
        del kwargs['certfile']
    return orig_starttls(self, *args, **kwargs)

smtplib.SMTP.starttls = starttls_patch


# ============================================================================
# CONFIGURAÇÕES DE CACHE - CORRIGIDAS
# ============================================================================

if USE_LOCAL_DB:
    # Cache em memória para desenvolvimento local
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'mobile-sps-cache',
            'TIMEOUT': 1800,  # 30 minutos (era 150 segundos - muito curto!)
            'OPTIONS': {
                'MAX_ENTRIES': 10000,  # Aumentar limite de entradas
            }
        }
    }
else:
    # Redis para produção
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 50,
                    'retry_on_timeout': True,
                    'socket_connect_timeout': 15,
                    'socket_timeout': 15,
                    'health_check_interval': 30,
                },
                'IGNORE_EXCEPTIONS': True,  # Não quebrar se Redis cair
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
            },
            'KEY_PREFIX': 'mobile_sps',
            'TIMEOUT': 3600,  # 1 hora
        }
    }

# ============================================================================
# CONFIGURAÇÕES DE SESSÃO - CORRIGIDAS E OTIMIZADAS
# ============================================================================

# Engine: cached_db é o mais robusto (usa cache + DB como fallback)
SESSION_ENGINE = os.getenv(
    'SESSION_ENGINE', 
    'django.contrib.sessions.backends.cached_db'
)

# Alias do cache usado para sessões
SESSION_CACHE_ALIAS = 'default'

# ⚠️ CORREÇÃO CRÍTICA: Aumentar tempo de expiração da sessão
SESSION_COOKIE_AGE = 86400  # 24 horas (era 3600 = 1 hora - MUITO CURTO!)

# ⚠️ CORREÇÃO CRÍTICA: Salvar sessão apenas quando modificada
# Isso evita conflitos em requisições concorrentes e erro de "session deleted"
SESSION_SAVE_EVERY_REQUEST = False

# Expirar sessão ao fechar o navegador (opcional - ajuste conforme necessidade)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # True = expira ao fechar navegador

# Nome do cookie de sessão (para evitar conflitos)
SESSION_COOKIE_NAME = 'mobile_sps_sessionid'

# Cookies de sessão: configurações de segurança
SESSION_COOKIE_SAMESITE = 'Lax'  # Ou 'Strict' para mais segurança
SESSION_COOKIE_HTTPONLY = True    # Proteger contra XSS
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS em produção

# Domínio do cookie (para compartilhar entre subdomínios)
SESSION_COOKIE_DOMAIN = os.getenv('SESSION_COOKIE_DOMAIN', None)

# Path do cookie
SESSION_COOKIE_PATH = '/'

# Serializer de sessão (JSON é mais seguro que pickle)
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# ============================================================================
# CONFIGURAÇÕES DE CSRF - CORRIGIDAS
# ============================================================================

CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True  # Adicionar proteção XSS
CSRF_COOKIE_NAME = 'mobile_sps_csrftoken'
CSRF_COOKIE_AGE = 31449600  # 1 ano (padrão Django)

# ⚠️ IMPORTANTE: Trusted origins para CSRF em produção
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:3000,http://localhost:8000'
).split(',')

# ============================================================================
# CELERY - CONFIGURAÇÕES
# ============================================================================

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_TASK_ALWAYS_EAGER = False
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'

# ============================================================================
# CONFIGURAÇÕES DE UPLOAD
# ============================================================================

DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024     # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024     # 100 MB
