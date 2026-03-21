import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# ALLOWED_HOSTS = []
# ALLOWED_HOSTS = ['10.129.165.187', '127.0.0.1', 'localhost']
ALLOWED_HOSTS = [
    'expense-tracker-with-templates.onrender.com',
]


# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # My apps
    'accounts.apps.AccountsConfig',
    'budget.apps.BudgetConfig',
    'expenses.apps.ExpensesConfig',
    'userSettings.apps.UsersettingsConfig',
    'dashboard.apps.DashboardConfig',
    'contact_app.apps.ContactAppConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'proj_expense_tracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'proj_expense_tracker.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# Using SQLite for Development
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Using PostgreSQL Database (Production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'expense_tracker_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_USER_MODEL = 'accounts.User'            #This Is Required


# --------- AUTHENTICATION Setting ------------------
# If your login view is at /account_app/login/ (notice singular "account")
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'  # Redirect to dashboard after login
LOGOUT_REDIRECT_URL = '/accounts/login/'



# CSRF Settings
CSRF_COOKIE_HTTPONLY = False  # ✅ Allow JavaScript to read CSRF cookie
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000']


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# -----------------------Email Configuration-------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
# -------------------------------------------------------------------------

# -----------------------Media Files Configuration---------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# -------------------------------------------------------------------------


# ---------------------JAZZMIN CONFIGURATION-------------------------
JAZZMIN_SETTINGS = {
    "site_title": "Expense Tracker Admin",
    "site_header": "Expense Tracker",
    "welcome_sign": "Welcome to the Expense Tracker Admin",
    "search_model": "auth.User",
    "show_sidebar": True,
    "navigation_expanded": True,
}

from decouple import config

SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-change-this-in-production')
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default='your-jwt-secret-key-change-this-in-production')