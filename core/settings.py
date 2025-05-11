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
print(ALLOWED_HOSTS)

USE_LOCAL_DB = config('USE_LOCAL_DB', default=True, cast=bool)

if USE_LOCAL_DB:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('LOCAL_DB_NAME'),
            'USER': config('LOCAL_DB_USER'),
            'PASSWORD': config('LOCAL_DB_PASSWORD'),
            'HOST': config('LOCAL_DB_HOST'),
            'PORT': config('LOCAL_DB_PORT'),
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
        }
    }


print("USE_LOCAL_DB =", USE_LOCAL_DB)
if USE_LOCAL_DB:
    print("DB_NAME usado =", config('LOCAL_DB_NAME'))
else:
    print("DB_NAME usado =", config('REMOTE_DB_NAME'))


DATABASE_ROUTERS = ['core.db_router.LicencaDBRouter']

# Definir aplicativos instalados
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'Licencas',
    'Produtos',
    'Entidades',
    'Pedidos',
    'dashboards',
    'Entradas_Estoque',
    'Saidas_Estoque',
    'listacasamento',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # <-- PRIMEIRO EXTERNO
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

TIME_ZONE = 'America/Sao_Paulo'
USE_TZ = True
USE_I18N = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
}


SIMPLE_JWT = {
    "USER_ID_FIELD": "usua_codi",
    "USER_ID_CLAIM": "usua_codi",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

APPEND_SLASH = True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # mantém os logs padrão do Django
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
            'formatter': 'verbose',  # troca pra 'simple' se quiser mais limpo
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',  # nível mínimo global
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        # logger do seu app
        'listacasamento.views': {  # substitui pelo nome real do seu app, tipo 'listas'
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
