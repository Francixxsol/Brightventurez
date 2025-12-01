import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'upej7vb)dpt%_ky7axfbd*)le&fzp()k0k#!@p3($&ti9%hx%&')
DEBUG = os.environ.get('DEBUG', 'True') 
ALLOWED_HOSTS = [
    "Brightventurez.online",
    "www.Brightventurez.online",
    "localhost",
    "127.0.0.1",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django_q",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "brightventurez.urls"

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
                "core.context_processors.global_context",
            ],
        },
    },
]

WSGI_APPLICATION = "brightventurez.wsgi.application"

# Use external Render database URL for local dev or fallback
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://brightventurez_db_fseb_user:9FytJndFBDOnKXh1gdnfe5IupVA27BWJ@dpg-d4maak7pm1nc73cptdcg-a.oregon-postgres.render.com/brightventurez_db_fseb'
)

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True  # keep True for security
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JS, images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [BASE_DIR / "static"]  # Only if you have a /static folder with extra files

# WhiteNoise static files storage
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Login settings
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"

# ===============================
# API KEYS (TEST KEYS YOU PROVIDED)
# ===============================
# Paystack
PAYSTACK_SECRET_KEY = "sk_test_e54dd453161e97d551ee75ad99ffc6ab1ecf25dd"
PAYSTACK_BASE_URL = "https://api.paystack.co"
PAYSTACK_CALLBACK_URL = "https://brightventurez.online/payment/verify/"  # production
PROVIDER_SUBACCOUNT = "ACCT_q1us193ulmhcyzo"

# VTU / ePins
VTU_API_KEY = "QvT8G9HlAjB3PQjIBHe5AunEwJfGxwfGmBJV3wzg9uI2gMuF8C"
VTU_BASE_URL = "https://api.epins.com.ng/sandbox/data/"
VTU_AIRTIME_URL = "https://api.epins.com.ng/sandbox/airtime/"

# platform split tuning (optional)
PLATFORM_MIN_PROFIT = 150
MIN_PLATFORM_PCT = 2
MAX_PLATFORM_PCT = 30
EXTERNAL_TIMEOUT = 20

DATA_PAYOUT = {
    "500MB": 80.00,
    "1GB": 240.00,
    "2GB": 450.00,
}

Q_CLUSTER = {
    "name": "brightventurez",
    "workers": 2,
    "timeout": 90,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",  # Use Django ORM
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-brightventurez-cache',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Or your email provider
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_USER')  # Your email
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASS')  # App password if Gmail
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
