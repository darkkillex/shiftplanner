import os, ssl, smtplib

from pathlib import Path
from datetime import timedelta
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key')
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'shiftplanner.urls'

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

WSGI_APPLICATION = 'shiftplanner.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'shiftplanner'),
        'USER': os.getenv('POSTGRES_USER', 'shiftplanner'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'shiftplanner'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=6),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'


# --- Lettura ENV ---
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"    # STARTTLS (587)
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"   # SSL (465)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))
EMAIL_SSL_SKIP_VERIFY = os.getenv("EMAIL_SSL_SKIP_VERIFY", "false").lower() == "true"  # solo per DEBUG
EMAIL_SENDER_MATCH_HOST_USER = os.getenv("EMAIL_SENDER_MATCH_HOST_USER", "true").lower() == "true"

EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Shift Planner")
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", EMAIL_HOST_USER or "no-reply@example.com")
DEFAULT_FROM_EMAIL = f"{EMAIL_FROM_NAME} <{EMAIL_FROM_ADDRESS}>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL  # per error emails
REPLY_TO_EMAIL = os.getenv("REPLY_TO_EMAIL", EMAIL_FROM_ADDRESS)

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

# --- Consistenza mittente ---
if EMAIL_SENDER_MATCH_HOST_USER and EMAIL_HOST_USER:
    # alcuni provider rifiutano From diverso dall'account autenticato
    DEFAULT_FROM_EMAIL = f"{EMAIL_FROM_NAME} <{EMAIL_HOST_USER}>"
    SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- Timeout SMTP ---
EMAIL_TIMEOUT = EMAIL_TIMEOUT

# --- Opzione (solo dev) per certificati TLS problematici ---
DEBUG = os.getenv("DEBUG", "true").lower() == "true"  # se non lo hai già
if DEBUG and EMAIL_SSL_SKIP_VERIFY and EMAIL_BACKEND.endswith("smtp.EmailBackend"):
    class UnsafeTLSBackend(DjangoSMTPBackend):
        """
        Forza STARTTLS con verifica disabilitata SOLO in DEBUG.
        Utile se il certificato del server SMTP non combacia con l'host.
        """
        def open(self):
            if self.connection:
                return False
            if self.use_ssl:
                ctx = ssl._create_unverified_context()
                self.connection = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=ctx)
            else:
                self.connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
                if self.use_tls:
                    ctx = ssl._create_unverified_context()
                    self.connection.starttls(context=ctx)
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"  # label resta uguale
    # monkeypatch “soft” per questa istanza
    import django.core.mail.backends.smtp as _smtp
    _smtp.EmailBackend = UnsafeTLSBackend