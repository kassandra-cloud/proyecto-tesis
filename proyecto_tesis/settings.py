"""
Django settings for proyecto_tesis project.
Django 5.0.x - Versión Final Blindada (Render / Railway / WAMPP)
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Paths & .env
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables desde .env en la raíz del proyecto
load_dotenv(os.path.join(BASE_DIR, '.env'))

import dj_database_url

# -------------------------------------------------------------------
# Seguridad / Debug (CORRECCIÓN: Definido al principio para evitar NameError)
# -------------------------------------------------------------------
SECRET_KEY = os.environ.get('SECRET_KEY', default='your-secret-key-123')
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# -------------------------------------------------------------------
# Hosts Permitidos y CSRF (Combinación Render + Railway + Local)
# -------------------------------------------------------------------
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Detección automática de Render
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Detección automática de Railway
RAILWAY_STATIC_URL = os.environ.get('RAILWAY_STATIC_URL')
if RAILWAY_STATIC_URL:
    ALLOWED_HOSTS.append(RAILWAY_STATIC_URL)

# Host específico de Railway por seguridad
ALLOWED_HOSTS.append("web-production-bb3bf.up.railway.app")

# IPs de desarrollo
ALLOWED_HOSTS.extend(["10.0.2.2", "192.168.231.132"])

# Orígenes confiables para CSRF (Necesario para Login en la nube)
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1",
    "http://localhost",
    "https://web-production-bb3bf.up.railway.app",
    "https://proyecto-tesis-final.onrender.com", # Reemplaza con tu link real de Render si es distinto
]

# -------------------------------------------------------------------
# Firebase (Admin SDK)
# -------------------------------------------------------------------
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY")
FIREBASE_PRIVATE_KEY_ID = os.getenv("FIREBASE_PRIVATE_KEY_ID", "")

# -----------------------------------------------------------------------------
# Apps
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
    "usuarios",
    "reuniones",
    "talleres",
    "votaciones",
    "foro",
    "anuncios",
    "recursos",
    "datamart",
    "widget_tweaks",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "channels",
    "storages",
]

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # Colocado arriba para estáticos
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.ForcePasswordChangeMiddleware",
    'core.middleware.BloqueoTotalVecinosMiddleware',
]

ROOT_URLCONF = "proyecto_tesis.urls"

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
# Base de datos (Lógica Inteligente Local vs Nube)
# -----------------------------------------------------------------------------
if DEBUG:
    # CONFIGURACIÓN WAMPP LOCAL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'junta_de_vecinos',
            'USER': 'root',
            'PASSWORD': '',
            'HOST': '127.0.0.1',
            'PORT': '3306',
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }
else:
    # CONFIGURACIÓN PRODUCCIÓN (Render / Railway)
    db_config = dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
    if 'OPTIONS' not in db_config:
        db_config['OPTIONS'] = {}
    
    db_config['OPTIONS']['ssl'] = {'ca': None}
    DATABASES = {'default': db_config}

# -----------------------------------------------------------------------------
# Password validators
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 14}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Archivos estáticos y media
# -----------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
# Redis / Celery / Channels
# -----------------------------------------------------------------------------
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE

# -----------------------------------------------------------------------------
# Caché (CORRECCIÓN: LocalMem para evitar error django_redis en local)
# -----------------------------------------------------------------------------
if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "tesis_bi",
        }
    }

# -----------------------------------------------------------------------------
# Almacenamiento S3 / Cellar
# -----------------------------------------------------------------------------
AWS_ACCESS_KEY_ID = os.environ.get('CELLAR_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('CELLAR_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('CELLAR_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = f"https://{os.environ.get('CELLAR_HOST')}" if os.environ.get('CELLAR_HOST') else ""
AWS_S3_REGION_NAME = "us-east-1"
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_SIGNATURE_VERSION = "s3v4"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# -----------------------------------------------------------------------------
# Otros
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/home"
LOGOUT_REDIRECT_URL = "/accounts/login/"

AUTHENTICATION_BACKENDS = [
    'core.authentication.LoginConCorreo',
    'django.contrib.auth.backends.ModelBackend',
]

APPSCRIPT_WEBHOOK_URL = os.getenv("APPSCRIPT_WEBHOOK_URL")
APPSCRIPT_WEBHOOK_SECRET = os.getenv("APPSCRIPT_WEBHOOK_SECRET")