# config/settings.py
import os
from pathlib import Path
from datetime import timedelta
import dj_database_url  # 🔥 NECESARIO PARA POSTGRES EN LA NUBE

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# --- CONFIGURACIÓN DE ENTORNO ---
# Detectamos si estamos en producción revisando si existe la variable DATABASE_URL
# (Railway/Render la inyectan automáticamente)
IS_PRODUCTION = 'DATABASE_URL' in os.environ

# SECRET KEY
# En producción lee la variable de entorno, en local usa la insegura
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-desarrollo-clave-default-local')

# DEBUG
# En producción debe ser False, en local True
DEBUG = 'RENDER' not in os.environ and 'RAILWAY_ENVIRONMENT' not in os.environ

ALLOWED_HOSTS = ['*'] # En producción idealmente pon tu dominio, pero '*' funciona para empezar.

# --- APLICACIONES ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceros
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # Tus Apps
    'core',
    'api',
    'shop',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # 🔥 VITAL: Debe ir justo después de Security
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',       # 🔥 VITAL: Antes de CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.ForceSessionMiddleware',      # Tu middleware personalizado
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- BASE DE DATOS (AUTO-SWITCH) ---
if IS_PRODUCTION:
    # Configuración para NUBE (PostgreSQL)
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Configuración para LOCAL (SQLite)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# --- VALIDADORES DE PASSWORD ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- IDIOMA Y ZONA HORARIA ---
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# --- ARCHIVOS ESTÁTICOS (WHITENOISE) ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Esto permite que WhiteNoise comprima y sirva los archivos en producción
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- ARCHIVOS MEDIA (IMÁGENES) ---
# Nota: En Railway/Render las imágenes se borran al redesplegar si no usas S3/Cloudinary.
# Para pruebas rápidas esto sirve, pero para producción real necesitarás un storage externo.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.Usuario'

# --- JWT CONFIGURACIÓN ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

# --- SESIONES ---
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'sessionid'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# --- SEGURIDAD: CORS Y CSRF (EL FIX PARA TU ERROR) ---
# Permite que cualquier origen se conecte (útil si tu frontend cambia de dominio o puerto)
CORS_ALLOW_ALL_ORIGINS = True 
CORS_ALLOW_CREDENTIALS = True

# Esto arregla el error "Origin untrustworthy"
CSRF_TRUSTED_ORIGINS = [
    "https://*.railway.app",  # Permite todos los subdominios de Railway
    "https://*.onrender.com", # Permite Render
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Ajustes de Cookies según entorno
if IS_PRODUCTION:
    SESSION_COOKIE_SECURE = True   # Solo enviar cookies por HTTPS
    CSRF_COOKIE_SECURE = True      # Solo enviar token CSRF por HTTPS
    SECURE_SSL_REDIRECT = True     # Forzar HTTPS siempre
    SESSION_COOKIE_SAMESITE = 'None' # Necesario para cross-site en algunos casos
    CSRF_COOKIE_SAMESITE = 'None'
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'

# --- REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'