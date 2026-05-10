import os
import sys
from pathlib import Path
from django.core.management.utils import get_random_secret_key
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
import dj_database_url

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
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '').strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '').strip()
GOOGLE_OAUTH_CONFIGURED_WITH_ENV = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)
GOOGLE_OAUTH_ENABLED = True
DEPLOYMENT_MANAGEMENT_COMMANDS = {'collectstatic', 'migrate'}


def is_deployment_management_command():
    if len(sys.argv) < 2 or Path(sys.argv[0]).name != 'manage.py':
        return False
    return sys.argv[1].strip().lower() in DEPLOYMENT_MANAGEMENT_COMMANDS


def build_secret_key():
    configured_key = os.getenv('SECRET_KEY', '').strip()
    known_placeholders = {
        'replace-this-with-a-long-random-secret-key',
        'changeme',
        'secret',
    }
    is_strong = (
        len(configured_key) >= 32
        and len(set(configured_key)) >= 5
        and not configured_key.startswith('django-insecure-')
        and configured_key.lower() not in known_placeholders
    )
    # In local development we prefer a stable key over regenerating one on
    # every reload, otherwise sessions and CSRF tokens break between requests.
    if configured_key and (DEBUG or is_strong):
        return configured_key
    if DEBUG:
        return 'django-insecure-vasu-local-development-secret-key'
    if is_deployment_management_command():
        # Render build and pre-deploy commands do not sign user-facing data, so
        # they can use an ephemeral key until the real production secret exists.
        return get_random_secret_key()
    raise ImproperlyConfigured(
        'Set a strong SECRET_KEY in your environment before running with DEBUG=False.'
    )


SECRET_KEY = build_secret_key()


def build_allowed_hosts():
    configured_hosts = env_list('ALLOWED_HOSTS')
    render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
    if render_hostname:
        configured_hosts.append(render_hostname)
    if DEBUG:
        configured_hosts.extend(['127.0.0.1', 'localhost', 'testserver'])
    hosts = list(dict.fromkeys(configured_hosts))
    if not DEBUG and not hosts:
        raise ImproperlyConfigured(
            'ALLOWED_HOSTS is required when DEBUG=False. Set it to your Render/custom domain.'
        )
    return hosts


ALLOWED_HOSTS = build_allowed_hosts()


def build_csrf_trusted_origins():
    configured_origins = env_list('CSRF_TRUSTED_ORIGINS')
    render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
    if render_hostname:
        configured_origins.append(f'https://{render_hostname}')
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
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
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
    'allauth.account.middleware.AccountMiddleware',
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
                'vasu.context_processors.seo_context',
                'aapcategory.context_product.memu_links',
                'aapstore.context_processors.cart_wishlist_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'vasu.wsgi.application'

AUTH_USER_MODEL = 'appaccounts.Account'
SITE_ID = env_int('SITE_ID', 1)

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_ADAPTER = 'appaccounts.adapters.VasuAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'appaccounts.adapters.VasuSocialAccountAdapter'
LOGIN_URL = 'login_register'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True

DATABASE_URL = os.getenv('DATABASE_URL', '').strip()

if not DATABASE_URL:
    raise ImproperlyConfigured(
        'DATABASE_URL is required. Configure Neon PostgreSQL; SQLite fallback is disabled.'
    )

DATABASES = {
    'default': dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=env_int('DB_CONN_MAX_AGE', 600),
        conn_health_checks=env_bool('DB_CONN_HEALTH_CHECKS', True),
        ssl_require=env_bool('DB_SSL_REQUIRE', True),
    )
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
MEDIA_ALLOWED_PATH_PREFIXES = ('photos', 'userprofile')
SERVE_MEDIA_FILES = env_bool('SERVE_MEDIA_FILES', True)

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

if DEBUG and (not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash").strip()
GEMINI_CHAT_ENABLED = env_bool("GEMINI_CHAT_ENABLED", bool(GEMINI_API_KEY and GEMINI_CHAT_MODEL))
GEMINI_CHAT_TIMEOUT = env_float("GEMINI_CHAT_TIMEOUT", 8.0)

# Backward compatibility aliases for existing references.
OPENAI_API_KEY = GEMINI_API_KEY
OPENAI_CHAT_MODEL = GEMINI_CHAT_MODEL
OPENAI_CHAT_ENABLED = GEMINI_CHAT_ENABLED
OPENAI_CHAT_TIMEOUT = GEMINI_CHAT_TIMEOUT
PAYMENT_UPI_ID = os.getenv("PAYMENT_UPI_ID", "7878065935@ptyes").strip()
PAYMENT_UPI_NAME = os.getenv("PAYMENT_UPI_NAME", "VASU").strip()
ANALYTICS_TRACKING_ENABLED = env_bool('ANALYTICS_TRACKING_ENABLED', True)

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
            'secret': os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    }
}

LOGIN_RATE_LIMIT_ATTEMPTS = env_int('LOGIN_RATE_LIMIT_ATTEMPTS', 5)
LOGIN_RATE_LIMIT_WINDOW_SECONDS = env_int('LOGIN_RATE_LIMIT_WINDOW_SECONDS', 900)
LOGIN_RATE_LIMIT_BLOCK_SECONDS = env_int('LOGIN_RATE_LIMIT_BLOCK_SECONDS', 900)
SEO_SITE_NAME = os.getenv('SEO_SITE_NAME', 'VASU Store').strip()
SEO_DEFAULT_DESCRIPTION = os.getenv(
    'SEO_DEFAULT_DESCRIPTION',
    'VASU is a luxury fashion store for women and men featuring designer collections, secure checkout, and premium support.',
).strip()
SEO_DEFAULT_OG_IMAGE = os.getenv('SEO_DEFAULT_OG_IMAGE', '/static/image/logo/logo-transparent.png').strip()
GOOGLE_SITE_VERIFICATION = os.getenv('GOOGLE_SITE_VERIFICATION', '').strip()
BING_SITE_VERIFICATION = os.getenv('BING_SITE_VERIFICATION', '').strip()
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', DEFAULT_FROM_EMAIL or 'support@localhost').strip()
PASSWORD_RESET_DOMAIN = os.getenv('PASSWORD_RESET_DOMAIN', '').strip()
PASSWORD_RESET_PROTOCOL = os.getenv('PASSWORD_RESET_PROTOCOL', '').strip().lower()
