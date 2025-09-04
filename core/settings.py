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
USE_LOCAL_DB = config('USE_LOCAL_DB', default=True, cast=bool)

# Configurações de banco de dados com otimizações
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
                'connect_timeout': 10,
                'application_name': 'mobile_sps',
            },
            'CONN_MAX_AGE': 300,  # 5 minutos para local
            'CONN_HEALTH_CHECKS': True,  # Verificar saúde das conexões
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
                'connect_timeout': 10,
                'application_name': 'mobile_sps',
            },
            'CONN_MAX_AGE': 600,  # 10 minutos para produção
            'CONN_HEALTH_CHECKS': True,  # Verificar saúde das conexões
        }
    }


import logging
logger = logging.getLogger("django")
logger.warning("🧠 BASE USADA: %s", "LOCAL" if USE_LOCAL_DB else "REMOTA")  # ← SEMPRE APARECE
logger.warning("🔗 CONFIGURAÇÃO DO BANCO: %s", DATABASES['default'])  # ← SEMPRE APARECE


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
    


]

# Middleware
MIDDLEWARE = [
    'core.performance_middleware.PerformanceMiddleware',  # PRIMEIRO
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.LicencaMiddleware',
    #'auditoria.middleware.AuditoriaMiddleware',  # REATIVAR ESTE
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
]

CORS_ALLOW_CREDENTIALS = True
ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

AUTHENTICATION_BACKENDS = [
    'Licencas.backends.UserBackend', 
]

AUTH_USER_MODEL = 'Licencas.Usuarios'

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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações do Django REST Framework com otimizações
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        #'Entidades.authentication.EntidadeJWTAuthentication', 
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',        
        'rest_framework.parsers.FormParser',       
        'rest_framework.parsers.MultiPartParser',  
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 25,  # Otimizado para performance
    'MAX_PAGE_SIZE': 100,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


SIMPLE_JWT = {
    "USER_ID_FIELD": "usua_codi",
    "USER_ID_CLAIM": "usua_codi",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
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
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['console'],
            'level': 'ERROR' if not DEBUG else 'WARNING',  # Reduce server logs
            'propagate': False,
        },
        'performance': {
            'handlers': ['console'],
            'level': 'WARNING' if not DEBUG else 'INFO',  # Only slow requests in production
            'propagate': False,
        },
        'core.utils': {
            'handlers': ['console'],
            'level': 'ERROR' if not DEBUG else 'WARNING',  # Reduce connection logs
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],  # Removido 'file'
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'Orcamentos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
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
        'ItensPedidosPisos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
            'formatter': 'verbose',
        },
        'performance': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
            'formatter': 'verbose',
        },



    },
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


# Cache Redis no container - configuração otimizada
if USE_LOCAL_DB:
    # Cache em memória para desenvolvimento local
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'mobile-sps-cache',
            'TIMEOUT': 3600,
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
                'IGNORE_EXCEPTIONS': True,
            },
            'KEY_PREFIX': 'mobile_sps',
            'TIMEOUT': 3600,
        }
    }

# Celery no container
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_TASK_ALWAYS_EAGER = False
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'

# Session no Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hora

