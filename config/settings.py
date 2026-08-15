import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Manual loader for local .env file
env_file = BASE_DIR / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-%k58&vjw)ai010%@t$xhi6i#hxfej!b-#r1c%!2f6pihx*lleg')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

# Vercel, Render va mahalliy xostlar uchun ruxsatlar
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()] if allowed_hosts_env else ['*']


# Application definition
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Men o'rnatgan applar
    'accounts',
    'pages',
    'articles',
    'comments',
    'pos',
    # Tashqi applar
    'rest_framework',
    'crispy_forms',
    'ckeditor',
    'ckeditor_uploader',
    'crispy_bootstrap5',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Statik fayllar uchun
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pos.middleware.UzbekScriptMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                'pos.context_processors.store_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
import os

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

if DB_NAME and DB_USER:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'frontend', 'dist'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Whitenoise orqali statik fayllarni siqish va saqlash
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.CustomUser'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
# Foydalanuvchi tizimga muvaffaqiyatli kirgandan keyin o'tadigan manzil

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CKEditor sozlamalari
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Full',
    }
}
CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_RESTRICT_BY_USER = True
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://web-production-5aab.up.railway.app',
    'http://127.0.0.1:8000',
    'http://localhost'
]


# ==========================================
# JAZZMIN ADMIN PANEL SETTINGS
# ==========================================
# ==========================================
# JAZZMIN ADMIN PANEL SETTINGS
# ==========================================
JAZZMIN_SETTINGS = {
    "site_title": "MeatFlow Pro — Boshqaruv Paneli",
    "site_header": "MeatFlow Pro",
    "site_brand": "MeatFlow Pro",
    "site_logo": "images/icon.jpg",
    "login_logo": "images/icon.jpg",
    "site_icon": "images/icon.jpg",
    "welcome_sign": "MeatFlow Pro Boshqaruv Paneliga Xush Kelibsiz",
    "copyright": "MeatFlow Pro Ltd © 2026",
    "search_model": ["pos.Customer", "pos.Sale", "pos.B2BOrder", "pos.Slaughter"],

    "topmenu_links": [
        {"name": "💻 POS Kassa", "url": "/pos/", "new_window": False},
        {"name": "📊 Dashboard", "url": "/", "new_window": False},
        {"name": "🤖 AI Qassob", "url": "/pos/ai-assistant/", "new_window": False},
        {"name": "👥 Mijozlar CRM", "url": "/pos/customers/", "new_window": False},
    ],

    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_models": ["auth.Group", "pos.AIChatMessage"],

    "icons": {
        "accounts.CustomUser": "fas fa-user-shield",
        "pos.B2BOrder": "fas fa-truck-loading",
        "pos.Sale": "fas fa-cash-register",
        "pos.Customer": "fas fa-users",
        "pos.Slaughter": "fas fa-drumstick-bite",
        "pos.Product": "fas fa-boxes",
        "pos.Stock": "fas fa-cubes",
        "pos.StockBatch": "fas fa-layer-group",
        "pos.Supplier": "fas fa-truck",
        "pos.CashTransaction": "fas fa-wallet",
        "pos.PaymentProof": "fas fa-file-invoice-dollar",
        "pos.Notebook": "fas fa-book-open",
        "pos.CustomerLog": "fas fa-history",
        "pos.StoreSetting": "fas fa-sliders-h",
        "pos.PaymentSetting": "fas fa-credit-card",
        "articles.Article": "fas fa-newspaper",
        "comments.Comment": "fas fa-comments",
    },

    "order_with_respect_to": [
        "pos.B2BOrder",
        "pos.Sale",
        "pos.Customer",
        "pos.Slaughter",
        "pos.Product",
        "pos.Stock",
        "pos.StockBatch",
        "pos.Supplier",
        "pos.CashTransaction",
        "pos.PaymentProof",
        "pos.Notebook",
        "pos.CustomerLog",
        "pos.StoreSetting",
        "pos.PaymentSetting",
        "accounts.CustomUser",
    ],

    "custom_css": "css/custom_admin.css",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-success",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-success",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

# ─── ESKIZ.UZ / SMS GATEWAY SETTINGS ───
SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'eskiz')
SMS_API_LOGIN = os.environ.get('ESKIZ_EMAIL', '')
SMS_API_PASSWORD = os.environ.get('ESKIZ_PASSWORD', '')
ESKIZ_EMAIL = SMS_API_LOGIN
ESKIZ_PASSWORD = SMS_API_PASSWORD

