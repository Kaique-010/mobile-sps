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
                'options': '-c timezone=America/Araguaina'
            },
            'CONN_MAX_AGE': 300,  # 5 minutos para local
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
                'options': '-c timezone=America/Araguaina'
            },
            'CONN_MAX_AGE': 600,  # 10 minutos para produção
        }
    }


import logging
logger = logging.getLogger("django")
logger.warning("🧠 BASE USADA: %s", "LOCAL" if USE_LOCAL_DB else "REMOTA")
logger.warning("🔗 CONFIGURAÇÃO DO BANCO: %s", DATABASES['default'])


DATABASE_ROUTERS = ['core.db_router.LicencaDBRouter']

# Cache para consultas frequentes (aplicado globalmente)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutos
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Definir aplicativos instalados
INSTALLED_APPS = [
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
    'sklearn',
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
    "Gerencial",
    "OrdemProducao",
    'parametros_admin',
    'mcp_agent_db',  
    'controledevisitas',

]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditoria.signals.AuditoriaSignalMiddleware', 
    'auditoria.middleware.AuditoriaMiddleware',
    'core.middleware.LicencaMiddleware',
]

# Configurações de CORS
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')

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
}

SIMPLE_JWT = {
    "USER_ID_FIELD": "usua_codi",
    "USER_ID_CLAIM": "usua_codi",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

APPEND_SLASH = True

# Configurações de timeout para produção
GUNICORN_TIMEOUT = 120  # 2 minutos

# Configurações de logging consolidadas
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{levelname}] {name}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'django_errors.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'Orcamentos': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'Entidades': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'Produtos': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'Pedidos': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'listacasamento.views': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
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
