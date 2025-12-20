"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Archivo de configuración global de Django. Contiene configuraciones 
               de base de datos, seguridad, aplicaciones instaladas, middleware, 
               archivos estáticos, Celery, correos y almacenamiento en la nube (S3).
--------------------------------------------------------------------------------
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from django.conf import settings

# -----------------------------------------------------------------------------
# Paths & .env
# -----------------------------------------------------------------------------
# Define el directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde un archivo .env en la raíz del proyecto
load_dotenv(os.path.join(BASE_DIR, '.env'))
import dj_database_url  # Utilidad para configurar DB desde una URL string

# -------------------------------------------------------------------
# Seguridad / Debug
# -------------------------------------------------------------------
# Clave secreta para firma criptográfica (debe venir desde .env en producción)
SECRET_KEY = os.environ.get('SECRET_KEY', default='your secret key')
# Modo Debug (True para desarrollo, False para producción)
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Lista de hosts/dominios permitidos para servir la aplicación
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME) # Añade host de Render si existe

# Agregar IPs locales para desarrollo si es necesario
ALLOWED_HOSTS.extend([
    "10.0.2.2",       # IP especial para emulador Android
    "192.168.231.132", # IP de red local ejemplo
])

# Orígenes confiables para CSRF (Cross-Site Request Forgery)
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1",
    "http://localhost",
    "http://10.0.2.2",
    "http://192.168.231.132:8000",
]

# -------------------------------------------------------------------
# Firebase (para Admin SDK y notificaciones push)
# -------------------------------------------------------------------
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY")
FIREBASE_PRIVATE_KEY_ID = os.getenv("FIREBASE_PRIVATE_KEY_ID", "")


# -----------------------------------------------------------------------------
# Apps (Aplicaciones Instaladas)
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # "daphne", # Servidor ASGI (comentado si se usa otro método de ejecución)
    "django.contrib.admin",       # Panel de administración
    "django.contrib.auth",        # Sistema de autenticación
    "django.contrib.contenttypes",# Tipos de contenido genéricos
    "django.contrib.sessions",    # Gestión de sesiones
    "django.contrib.messages",    # Mensajes flash
    "django.contrib.staticfiles", # Archivos estáticos

    # Project apps (Módulos desarrollados por el equipo)
    "core.apps.CoreConfig",
    "usuarios",
    "reuniones",
    "talleres",
    "votaciones",
    "foro",
    "anuncios",
    "recursos",
    "datamart",

    # Terceros (Librerías externas)
    "widget_tweaks",             # Mejoras en renderizado de formularios
    "rest_framework",            # API REST Framework
    "rest_framework.authtoken",  # Autenticación por Token para API
    "django_filters",            # Filtrado avanzado en API
    "channels",                  # WebSockets
    "storages",                  # Almacenamiento en S3/Cloud
]

# -----------------------------------------------------------------------------
# Middleware (Procesadores de petición/respuesta)
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.ForcePasswordChangeMiddleware",   # Fuerza cambio de clave inicial
    'core.middleware.BloqueoTotalVecinosMiddleware',   # Bloquea acceso a vecinos inactivos
    'whitenoise.middleware.WhiteNoiseMiddleware',      # Sirve estáticos en producción
    'proyecto_tesis.middleware.MonitorRendimientoMiddleware', # Mide performance
]

# Archivo principal de rutas URL
ROOT_URLCONF = "proyecto_tesis.urls"

# -----------------------------------------------------------------------------
# Templates (Plantillas HTML)
# -----------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"], # Directorio global de templates
        "APP_DIRS": True, # Buscar templates dentro de cada app
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

# Definición de aplicaciones WSGI y ASGI
ASGI_APPLICATION = "proyecto_tesis.asgi.application"
WSGI_APPLICATION = "proyecto_tesis.wsgi.application"

# -----------------------------------------------------------------------------
# Base de datos (Configuración compatible con TiDB Cloud / Aiven)
# -----------------------------------------------------------------------------
db_config = dj_database_url.config(
    default=os.getenv('DATABASE_URL', 'mysql://root:@127.0.0.1:3306/prueba'),
    conn_max_age=600,         # Persistencia de conexiones
    conn_health_checks=True,  # Verificar salud de conexión
)

# 1. Asegurar que el diccionario 'OPTIONS' exista
if 'OPTIONS' not in db_config:
    db_config['OPTIONS'] = {}

# 2. Corregir error 'unexpected keyword argument ssl_mode' limpiando parámetros incompatibles
if 'ssl_mode' in db_config['OPTIONS']:
    db_config['OPTIONS'].pop('ssl_mode')
if 'ssl-mode' in db_config['OPTIONS']:
    db_config['OPTIONS'].pop('ssl-mode')

# 3. Forzar conexión segura compatible con TiDB Cloud y Aiven (SSL sin verificación estricta de CA local)
db_config['OPTIONS']['ssl'] = {'ca': None}

DATABASES = {
    'default': db_config
}

# 4. Opciones de compatibilidad adicionales para MySQL/TiDB
DATABASES['default']['OPTIONS'].update({
    "connect_timeout": 10,
    "charset": "utf8mb4",
    "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
})

# -----------------------------------------------------------------------------
# Validadores de contraseñas
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 14}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# Internacionalización y Zona Horaria
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "es-cl" # Español de Chile
TIME_ZONE = "America/Santiago" # Hora de Chile
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Redirecciones de Autenticación
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
MEDIA_ROOT = BASE_DIR / "media" # Carpeta local para subidas (si no se usa S3)

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # Carpeta para collectstatic

# --- Configuración de WhiteNoise (Para servir estáticos eficientemente en producción) ---
if not DEBUG:
    STATIC_URL = '/static/'
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# -----------------------------------------------------------------------------
# Límites de tamaño de subida
# -----------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50 MB límite
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50 MB límite

# -----------------------------------------------------------------------------
# Configuración DRF (Django REST Framework)
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",   # Auth por Token (Móvil)
        "rest_framework.authentication.SessionAuthentication", # Auth por Sesión (Web)
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}

# -----------------------------------------------------------------------------
# Configuración de Email (SMTP - Gmail)
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

# Configuración de Channels (Capa de canales para WebSockets usando Redis)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379/1')],
        },
    }
}

# Configuración del modelo de reconocimiento de voz (Vosk)
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
# =================================================

# Credenciales desde variables de entorno
AWS_ACCESS_KEY_ID = os.environ.get('CELLAR_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('CELLAR_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('CELLAR_BUCKET_NAME')

# Endpoint para servicio compatible con S3 (Cellar)
AWS_S3_ENDPOINT_URL = f"https://{os.environ.get('CELLAR_HOST')}"
AWS_S3_REGION_NAME = "us-east-1" # Región por defecto para compatibilidad

# --- CRÍTICO: Configuración "Path Style" para evitar errores de DNS en buckets ---
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_SIGNATURE_VERSION = "s3v4"

# Configuraciones de comportamiento de archivos
AWS_S3_FILE_OVERWRITE = False  # No sobrescribir si el nombre ya existe (añade sufijo)
AWS_DEFAULT_ACL = None         # Dejar privacidad al bucket policy
AWS_S3_VERIFY = True           # Verificar certificados SSL
AWS_S3_USE_SSL = True

# Cache control para mejorar rendimiento de descarga
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

# Seguridad de enlaces
if DEBUG:
    # En desarrollo, URLs con autenticación querystring
    AWS_QUERYSTRING_AUTH = True
else:
    # En producción, URLs firmadas temporalmente
    AWS_QUERYSTRING_AUTH = True

# --- BACKEND DE ALMACENAMIENTO ---
# Define que Django use S3Boto3Storage para campos FileField/ImageField
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# =================================================
# --- BACKENDS DE AUTENTICACIÓN ---
# =================================================
AUTHENTICATION_BACKENDS = [
    'core.authentication.LoginConCorreo',       # Personalizado: Login con email
    'django.contrib.auth.backends.ModelBackend', # Estándar: Login con username
]

# =================================================
# --- WEBHOOK GOOGLE APPS SCRIPT (ENVÍO DE CORREO DE EMERGENCIA) ---
# =================================================
APPSCRIPT_WEBHOOK_URL = os.getenv("APPSCRIPT_WEBHOOK_URL")
APPSCRIPT_WEBHOOK_SECRET = os.getenv("APPSCRIPT_WEBHOOK_SECRET")

# =================================================
# --- CONFIGURACIÓN DE CACHÉ (REDIS) ---
# =================================================
# Configura Redis como backend de caché compartido
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        "TIMEOUT": 120,  # Tiempo de vida por defecto: 2 minutos
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "tesis_bi", # Prefijo para claves en Redis
    }
}