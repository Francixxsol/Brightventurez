import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
   'whitenoise.middleware.WhiteNoiseMiddleware',
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
                # 👇 our custom context processor
                "core.context_processors.global_context",
            ],
        },
    },
]

WSGI_APPLICATION = "brightventurez.wsgi.application"

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

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Static files (CSS, JS, images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===============================
# API KEYS (TEST KEYS YOU PROVIDED)
# ===============================
PAYSTACK_SECRET_KEY = "sk_test_e54dd453161e97d551ee75ad99ffc6ab1ecf25dd"
PAYSTACK_PUBLIC_KEY = "pk_test_1eedbe095ff5fb2a643afdd0d4a51d10e1849f45"
PAYSTACK_BASE_URL = "https://api.paystack.co"

VTU_API_KEY = "3e1aafc7efe00b49a0f640049b7ac7"
VTU_BASE_URL = "https://vtu.com.ng/API/"

# Sell data default payouts (editable later in DB or Admin)
DATA_PAYOUT = {
    "500MB": 80.00,
    "1GB": 240.00,
    "2GB": 450.00,
}

import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'upej7vb)dpt%_ky7axfbd*)le&fzp()k0k#!@p3($&ti9%hx%&')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['brightventurez.onrender.com', 'localhost', '127.0.0.1']

# Database configuration
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# If you have extra static folders:
# STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise static files storage (for best practice)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Login settings
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
