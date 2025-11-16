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
load_dotenv(BASE_DIR / ".env")

# -----------------------------------------------------------------------------
# Seguridad / Debug
# -----------------------------------------------------------------------------
# Usa la clave desde .env; genera una para prod. La que sigue es solo fallback DEV.
SECRET_KEY = os.getenv("SECRET_KEY", "DEV-ONLY-CHANGE-ME")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    # Desarrollo local / emuladores / dispositivos en tu Wi-Fi
    "127.0.0.1",
    "localhost",
    "10.0.2.2",
    "192.168.0.101",   # IP de tu PC en la red (ajústala si cambia)
]

# Si usas login vía sesión desde Android/web, conviene permitir CSRF
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1",
    "http://localhost",
    "http://10.0.2.2",
    "http://192.168.0.101:8000",
]

# -----------------------------------------------------------------------------
# Apps
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # "daphne",  #
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
        "CONN_MAX_AGE": 0,            # reutiliza la conexión hasta 60s
        "CONN_HEALTH_CHECKS": True,    # Django 5: revisa conexión antes de usarla
        "OPTIONS": {
            "connect_timeout": 10,
        },
        "OPTIONS": {
            "connect_timeout": 10,  # <-- De la primera
            "charset": "utf8mb4",   # <-- De la segunda
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'", # <-- De la segunda
        }
    }
}

# -----------------------------------------------------------------------------
# Password validators
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
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
# Email (SMTP) — usa variables de entorno
# -----------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# -----------------------------------------------------------------------------
# Producción (sugerencias, descomenta cuando pases a HTTPS/CDN)
# -----------------------------------------------------------------------------
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# -----------------------------------------------------------------------------
# Clave primaria por defecto
# -----------------------------------------------------------------------------
# --- Channels (capa en memoria para desarrollo) ---
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MODEL_PATH_RELATIVO= Path(r"vosk-model-small-es-0.42")
MODEL_PATH = os.path.join(settings.BASE_DIR, MODEL_PATH_RELATIVO)

# =================================================
# --- CONFIGURACIÓN DE CELERY (CON REDIS) ---
# =================================================
# Lee la variable 'REDIS_URL' que pusiste en tu .env
CELERY_BROKER_URL = os.environ.get('REDIS_URL')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# =================================================
# --- CONFIGURACIÓN DE CLEVER CLOUD STORAGE (CELLAR) ---
# =================================================
# Lee las variables de Cellar que pusiste en tu .env
AWS_ACCESS_KEY_ID = os.environ.get('CELLAR_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('CELLAR_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('CELLAR_BUCKET_NAME')
AWS_S3_REGION_NAME = 'US' 
AWS_S3_ENDPOINT_URL = f"https://{os.environ.get('CELLAR_HOST')}"

# Configuración de django-storages
AWS_DEFAULT_ACL = None
AWS_S3_USE_SSL = True
AWS_S3_VERIFY = True

# Define el backend de almacenamiento
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# (Opcional) Si quieres que tus archivos estáticos (CSS/JS) también
# se sirvan desde Cellar en producción (¡recomendado!):
# if not DEBUG:
#     STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'