import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

try:
    import dj_database_url
except ImportError:  # pragma: no cover - optional in local dev until installed
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    return default


def env_list(name, default=None):
    value = os.getenv(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


def env_int(name, default=0):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def env_float(name, default=0.0):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


DEBUG = env_bool('DEBUG', True)


def build_secret_key():
    configured_key = os.getenv('SECRET_KEY', '').strip()
    is_strong = (
        len(configured_key) >= 50
        and len(set(configured_key)) >= 5
        and not configured_key.startswith('django-insecure-')
    )
    # In local development we prefer a stable key over regenerating one on
    # every reload, otherwise sessions and CSRF tokens break between requests.
    if configured_key and (DEBUG or is_strong):
        return configured_key
    if DEBUG:
        return 'django-insecure-vasu-local-development-secret-key'
    raise ImproperlyConfigured(
        'Set a strong SECRET_KEY in your environment before running with DEBUG=False.'
    )


SECRET_KEY = build_secret_key()

ALLOWED_HOSTS = ['*']

def build_csrf_trusted_origins():
    configured_origins = env_list('CSRF_TRUSTED_ORIGINS')
    if DEBUG:
        configured_origins.extend([
            'http://localhost',
            'http://127.0.0.1',
            'http://localhost:8000',
            'http://127.0.0.1:8000',
        ])
    return list(dict.fromkeys(configured_origins))


CSRF_TRUSTED_ORIGINS = build_csrf_trusted_origins()

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'appwomens.apps.AppwomensConfig',
    'appmens.apps.AppmensConfig',
    'appaccounts',
    'aapcategory',
    'aapstore',
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

APPEND_SLASH = True

ROOT_URLCONF = 'vasu.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'aapcategory.context_product.memu_links',
                'aapstore.context_processors.cart_wishlist_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'vasu.wsgi.application'

AUTH_USER_MODEL = 'appaccounts.Account'

DATABASE_URL = os.getenv('DATABASE_URL', '').strip()

if DATABASE_URL and dj_database_url is not None:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=env_int('DB_CONN_MAX_AGE', 600),
            ssl_require=env_bool('DB_SSL_REQUIRE', not DEBUG),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

USE_HTTPS_SECURITY = env_bool('USE_HTTPS_SECURITY', not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000' if USE_HTTPS_SECURITY else '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', USE_HTTPS_SECURITY)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', USE_HTTPS_SECURITY)
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', USE_HTTPS_SECURITY)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', USE_HTTPS_SECURITY)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', USE_HTTPS_SECURITY)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '465'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', False)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', True)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'webmaster@localhost')

JAZZMIN_SETTINGS = {
    "site_title" : "VASU",
    "site_header" : "VASU",
    "site_brand" : "VASU",
    "site_logo" : "image/logo/logo-transparent.png", 
    "login_logo": "image/logo/logo-transparent.png",
    "welcome_sign": "Welcome to the VASU Admin Panael",
    "copyright": "VASU PVT.LTD",
    "site_url": "http://vasu.io",
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"app": "appmens"},
        {"app": "appwomens"},
        {"app": "aapcategory"},
        {"model": "appaccounts.Account"},  
    ],
    "icons": {
        "aapcategory.Category": "fas fa-list",   
        "aapcategory.Designer": "fas fa-pen-nib",
        "aapstore.Product": "fas fa-box-open",
        "aapstore.Cart": "fas fa-shopping-cart",
        "aapstore.Wishlist": "fas fa-heart",
        "aapstore.Order": "fas fa-clipboard-list",    
        "aapstore.OrderItem": "fas fa-box-open",
        "appaccounts.Account": "fas fa-user-circle",
        "appmens.Accessories": "fas fa-glasses",
        "appmens.Bags": "fas fa-shopping-bag",
        "appmens.Clothing": "fas fa-tshirt",
        "appmens.Dresses": "fas fa-female",
        "appmens.Footwear": "fas fa-shoe-prints",
        "appmens.Happenings": "fas fa-bolt",
        "appmens.SaleItems": "fas fa-tags",
        "appmens.HomeTemplate": "fas fa-home",
        "appwomens.Accessories": "fas fa-glasses",
        "appwomens.Bags": "fas fa-shopping-bag",
        "appwomens.Clothing": "fas fa-tshirt",
        "appwomens.Dresses": "fas fa-female",
        "appwomens.Footwear": "fas fa-shoe-prints",
        "appwomens.Happenings": "fas fa-bolt",
        "appwomens.SaleItems": "fas fa-tags",
        "appwomens.Shops": "fas fa-soap",
        "appwomens.BeautyProducts": "fas fa-air-freshener",
        "appwomens.HomeTemplate": "fas fa-home",
        "appwomens.Kendalls_editions": "fas fa-camera-retro",
        "appwomens.NewProduct": "fas fa-box-open",
        "appwomens.ProductVariation": "fas fa-layer-group",
        "appmens.NewProduct": "fas fa-box-open",
        "appmens.ProductVariation": "fas fa-layer-group",
    },
    "custom_css": "admin/css/admin.css", 
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
    "dark_mode_theme": "flatly",
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_ENABLED = env_bool("OPENAI_CHAT_ENABLED", False)
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "").strip()
OPENAI_CHAT_TIMEOUT = env_float("OPENAI_CHAT_TIMEOUT", 6.0)
PAYMENT_UPI_ID = os.getenv("PAYMENT_UPI_ID", "7878065935@ptyes").strip()
PAYMENT_UPI_NAME = os.getenv("PAYMENT_UPI_NAME", "VASU").strip()
