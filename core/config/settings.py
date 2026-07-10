import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'colocar_chave_do_django_aqui')
DEBUG = os.getenv('DEBUG', 'True').strip().lower() == 'true'
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
    'django_prometheus',
    'corsheaders', # CORS
    'accounts',
    'program',
    'collection',
    'custom_audit',
    'reports',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # middleware de CORS
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'custom_audit.middleware.CustomAuditMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Origens permitidas no CORS
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3001",
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
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise serve os estáticos (admin, DRF browsable API) sob gunicorn,
# inclusive com DEBUG=False, sem depender de um servidor web externo.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

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

# Google OAuth2
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

# DeepSeek API Key
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')


# LLM local via LM Studio (OpenAI-compatible)
LOCAL_LLM_BASE_URL = os.getenv('LOCAL_LLM_BASE_URL', 'http://host.docker.internal:1234')
LOCAL_LLM_MODEL = os.getenv('LOCAL_LLM_MODEL', 'google/gemma-4-e2b')
