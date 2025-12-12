"""
Django settings for proyecto_tesis project.
Django 5.0.x
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from django.conf import settings

# -----------------------------------------------------------------------------
# Paths & .env
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables desde .env en la raíz del proyecto
load_dotenv(os.path.join(BASE_DIR, '.env'))


# -------------------------------------------------------------------
# Seguridad / Debug
# -------------------------------------------------------------------
# Clave secreta (debe venir desde .env en producción)
SECRET_KEY = os.environ.get('SECRET_KEY', default='your secret key')
# DEBUG=True/False en .env
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Hosts permitidos
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Agregar IPs locales para desarrollo si es necesario
ALLOWED_HOSTS.extend([
    "10.0.2.2",
    "192.168.231.132",
])

# CSRF
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1",
    "http://localhost",
    "http://10.0.2.2",
    "http://192.168.231.132:8000",
]

# -------------------------------------------------------------------
# Firebase (para Admin SDK)
# -------------------------------------------------------------------
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY")
FIREBASE_PRIVATE_KEY_ID = os.getenv("FIREBASE_PRIVATE_KEY_ID", "")


# -----------------------------------------------------------------------------
# Apps
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Project apps
    "core.apps.CoreConfig",
    "usuarios",
    "reuniones",
    "talleres",
    "votaciones",
    "foro",
    "anuncios",
    "recursos",
    "datamart",

    # Terceros
    "widget_tweaks",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "channels",
    "storages",  # <--- CORRECCIÓN 1: Agregado para que funcione S3/Cellar
]

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.ForcePasswordChangeMiddleware",
    # Eliminado duplicado de SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'proyecto_tesis.middleware.MonitorRendimientoMiddleware',
]

ROOT_URLCONF = "proyecto_tesis.urls"

# -----------------------------------------------------------------------------
# Templates
# -----------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "proyecto_tesis.asgi.application"
WSGI_APPLICATION = "proyecto_tesis.wsgi.application"


# -----------------------------------------------------------------------------
# Base de datos (MySQL via .env)
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "prueba"),
        "USER": os.getenv("MYSQL_USER", "root"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "CONN_MAX_AGE": 0 if DEBUG else 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}


# -----------------------------------------------------------------------------
# Password validators
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 14}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# I18N / TZ
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Auth redirects
# -----------------------------------------------------------------------------
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/home"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# -----------------------------------------------------------------------------
# Archivos estáticos y media
# -----------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# --- Configuración de WhiteNoise (Producción) ---
if not DEBUG:
    STATIC_URL = '/static/'
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# -----------------------------------------------------------------------------
# Tamaños de subida
# -----------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50 MB

# -----------------------------------------------------------------------------
# DRF
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}

# -----------------------------------------------------------------------------
# Email (SMTP)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# -----------------------------------------------------------------------------
# Configuración adicional
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379/1')],
        },
    }
}

# Modelo Vosk
MODEL_PATH_RELATIVO = Path(r"vosk-model-small-es-0.42")
MODEL_PATH = os.path.join(settings.BASE_DIR, MODEL_PATH_RELATIVO)

# =================================================
# --- CONFIGURACIÓN DE CELERY (CON REDIS) ---
# =================================================
CELERY_BROKER_URL = os.environ.get('REDIS_URL')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# =================================================
# --- CONFIGURACIÓN DE CLEVER CLOUD STORAGE (CELLAR / S3) ---
# CORRECCIÓN 2 y 3: Bloque unificado y corregido
# =================================================

# Credenciales desde .env
AWS_ACCESS_KEY_ID = os.environ.get('CELLAR_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('CELLAR_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('CELLAR_BUCKET_NAME')

# Endpoint para Cellar
AWS_S3_ENDPOINT_URL = f"https://{os.environ.get('CELLAR_HOST')}"
AWS_S3_REGION_NAME = "us-east-1" # Cellar funciona bien con la región default de boto3

# --- CRÍTICO: Configuración "Path Style" para Cellar ---
# Esto evita que Django intente conectar a bucket.cellar.services...
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_SIGNATURE_VERSION = "s3v4"

# Configuraciones de Archivos
AWS_S3_FILE_OVERWRITE = False  # No sobrescribir si el nombre ya existe
AWS_DEFAULT_ACL = None         # Dejar privacidad al bucket
AWS_S3_VERIFY = True           # Verificar SSL
AWS_S3_USE_SSL = True

# Cache control (Opcional, mejora rendimiento)
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

# Seguridad de enlaces firmados (Privacidad)
if DEBUG:
    # En desarrollo, URLs públicas para facilitar pruebas
    AWS_QUERYSTRING_AUTH = True
else:
    # En producción, URLs firmadas que expiran (seguridad)
    AWS_QUERYSTRING_AUTH = True

# --- BACKEND DE ALMACENAMIENTO ---
# Esto le dice a Django que use S3/Cellar para FileField
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# =================================================
# --- AUTHENTICATION BACKENDS ---
# =================================================
AUTHENTICATION_BACKENDS = [
    'core.authentication.LoginConCorreo',
    'django.contrib.auth.backends.ModelBackend',
]
# =================================================
# --- WEBHOOK GOOGLE APPS SCRIPT (ENVÍO DE CORREO) ---
# =================================================
APPSCRIPT_WEBHOOK_URL = os.getenv("APPSCRIPT_WEBHOOK_URL")
APPSCRIPT_WEBHOOK_SECRET = os.getenv("APPSCRIPT_WEBHOOK_SECRET")