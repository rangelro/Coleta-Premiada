import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'chave-local-insegura')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'accounts',
    'program',
    'collection',

    'auditlog' #auditoria
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', # middleware de auditoria
    'auditlog.middleware.AuditlogMiddleware', # middleware de auditoria
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# PostgreSQL via Docker ou local
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     os.getenv('POSTGRES_DB',       'coleta_premiada'),
        'USER':     os.getenv('POSTGRES_USER',     'coleta_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'coleta_senha_local'),
        'HOST':     os.getenv('POSTGRES_HOST',     'localhost'),
        'PORT':     os.getenv('POSTGRES_PORT',     '5432'),
    }
}

# JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.Usuario'
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Fortaleza'
USE_TZ = True

# O restante das configurações padrão do Django mantidas para evitar erros:
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

WSGI_APPLICATION = 'config.wsgi.application'

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

STATIC_URL = 'static/'

# ---------------------------------------------------------------------------
# Celery — broker = mesmo RabbitMQ usado pelo messaging
# ---------------------------------------------------------------------------
_rmq_user = os.getenv('RABBITMQ_DEFAULT_USER', 'guest')
_rmq_pass = os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')
_rmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
_rmq_port = os.getenv('RABBITMQ_PORT', '5672')

CELERY_BROKER_URL = os.getenv(
    'CELERY_BROKER_URL',
    f'amqp://{_rmq_user}:{_rmq_pass}@{_rmq_host}:{_rmq_port}/',
)
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# User-agent enviado ao Nominatim — deve identificar o projeto
NOMINATIM_USER_AGENT = os.getenv('NOMINATIM_USER_AGENT', 'coleta-premiada/1.0')

# Anthropic API Key
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
