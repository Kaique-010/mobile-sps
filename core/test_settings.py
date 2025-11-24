from .settings import *

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

REST_FRAMEWORK = REST_FRAMEWORK

SIMPLE_JWT = SIMPLE_JWT

USE_TZ = True
TIME_ZONE = 'America/Araguaina'