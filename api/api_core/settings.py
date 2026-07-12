import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

MODE = os.getenv('MODE', 'dev')
USE_SQLITE = os.getenv('USE_SQLITE', '1') == '1'
DEBUG = os.getenv('DEBUG', '1') == "1"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "INSECURE_SECRET_KEY")

# DOMAIN_NAME is the single public-facing entrypoint: a domain (flowless.example.com)
# or an ip:port (192.168.1.204:8004). A leading scheme is tolerated and stripped.
# Origins (CORS/CSRF) and ALLOWED_HOSTS are derived from it, accepting http and https.
DOMAIN_NAME = os.getenv("DOMAIN_NAME", "").strip()
if "://" in DOMAIN_NAME:
    DOMAIN_NAME = urlparse(DOMAIN_NAME).netloc

PUBLIC_ORIGINS = [f"https://{DOMAIN_NAME}", f"http://{DOMAIN_NAME}"] if DOMAIN_NAME else []

_domain_host = urlparse(f"//{DOMAIN_NAME}").hostname if DOMAIN_NAME else None
ALLOWED_HOSTS = list(dict.fromkeys(
    host for host in [_domain_host, "localhost", "127.0.0.1"] if host
))

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT'),
        }
    }

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_celery_beat',
    'corsheaders',
    'djx_account',
    'djx_websocket',
    'channels',
    'project_ops',
    "media_source",
    "tv_channel",
    "grid_schedule",
    "rule_engine",
    "grid_layout_preset",
    "editorial_planning",
    "dashboard",
]

if MODE == 'dev':
    INSTALLED_APPS += [
        "djx_cmds"
    ]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'api_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# WSGI_APPLICATION = 'api_core.wsgi.application'
ASGI_APPLICATION = 'api_core.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_ROOT = os.path.join(BASE_DIR, "statics")
MEDIA_ROOT = os.path.join(BASE_DIR, 'medias')

if MODE == 'prod':
    MEDIA_URL = os.getenv('MEDIA_URL', '/medias/')
    STATIC_URL = os.getenv('STATIC_URL', '/statics/')
else:
    MEDIA_URL = '/medias/'
    STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# cors

CORS_ALLOWED_ORIGINS = PUBLIC_ORIGINS
CORS_ALLOW_ALL_ORIGINS = False

# csrf
CSRF_TRUSTED_ORIGINS = PUBLIC_ORIGINS

# DRF

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",

    ],
    "DEFAULT_AUTHENTICATION_CLASSES":
        [
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        ],
}

# JWT

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=10),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,

    'ALGORITHM': 'HS256',
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Email

MAIL_SYSTEM = os.getenv("MAIL_SYSTEM", "anymail")

if MAIL_SYSTEM.lower() == "anymail":

    # ANYMAIL

    EMAIL_BACKEND = "anymail.backends.sendinblue.EmailBackend"

    ANYMAIL = {
        "SENDINBLUE_API_KEY": os.getenv('SENDINBLUE_API_KEY'),
    }

else:
    # BASIC EMAIL
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '1') == '1'
    EMAIL_PORT = os.getenv('EMAIL_PORT', 587)
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

AUTH_USER_MODEL = "djx_account.User"

DJX_ACCOUNT = {
    "USER_CONFIRMATION_TOKEN_TTL": 60 * 60 * 24,
    "USER_PASSWORD_RESET_TOKEN_TTL": 60 * 60,
    "LINKEDIN": {
        "CLIENT_ID": os.getenv("LINKEDIN_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("LINKEDIN_CLIENT_SECRET")
    },
    "TWITTER": {
        "CLIENT_ID": os.getenv("TWITTER_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("TWITTER_CLIENT_SECRET")
    },
    "MICROSOFT": {
        "CLIENT_ID": os.getenv("MICROSOFT_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("MICROSOFT_CLIENT_SECRET")
    },
    "FACEBOOK": {
        "CLIENT_ID": os.getenv("FACEBOOK_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("FACEBOOK_CLIENT_SECRET")
    },
    "DISCORD": {
        "CLIENT_ID": os.getenv("DISCORD_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("DISCORD_CLIENT_SECRET")
    },
    "GOOGLE": {
        "CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET")
    },

    "DEFAULT_ADMIN_USERNAME": os.getenv("DEFAULT_ADMIN_USERNAME"),
    "DEFAULT_ADMIN_EMAIL": os.getenv("DEFAULT_ADMIN_EMAIL"),
    "DEFAULT_ADMIN_PASSWORD": os.getenv("DEFAULT_ADMIN_PASSWORD"),
    "CLIENT_USER_CONFIRMATION_TOKEN_URL": os.getenv("CLIENT_USER_CONFIRMATION_TOKEN_URL"),
    "CLIENT_USER_PASSWORD_RESET_TOKEN_URL": os.getenv("CLIENT_USER_PASSWORD_RESET_TOKEN_URL")
}

# Channel / Websocket

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.getenv('REDIS_HOST'), os.getenv('REDIS_PORT'))],
        },
    },
}

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_USE_SSL = False
CELERY_BROKER_URL = f"{'rediss' if CELERY_USE_SSL else 'redis'}://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_URL = os.getenv("LLM_URL", "http://192.168.1.223:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5")

CATALOG_GENERATOR_MAX_CHANNELS = int(os.getenv("CATALOG_GENERATOR_MAX_CHANNELS", "30"))
LLM_RETRY_CATALOG_CHANNEL_GENERATION = int(os.getenv("LLM_RETRY_CATALOG_CHANNEL_GENERATION", 3))
EDITORIAL_LINE_LLM_MAX_ATTEMPTS = int(os.getenv("EDITORIAL_LINE_LLM_MAX_ATTEMPTS", "3"))

ETV_BASE_URL = os.getenv("ETV_BASE_URL")
ETV_API_BASE_URL = os.getenv("ETV_API_BASE_URL")
ETV_API_WRAPPER_FILE_PATH = os.getenv("ETV_API_WRAPPER_FILE_PATH")

DAYS_TO_BUILD = 3  # Nombre de jour que l'on build a l'avance
SCAN_MEDIA_EVERY_HOURS = 3  # on scan les collections active chaque...
MEDIA_CONTAINER_ANALYSE_USE_LLM = os.getenv("MEDIA_CONTAINER_ANALYSE_USE_LLM", "0") == "1"
MEDIA_COLLECTION_SYNC_BATCH_SIZE = int(os.getenv("MEDIA_COLLECTION_SYNC_BATCH_SIZE", 10))

LLM_RETRY_BLUEPRINT = 1
LLM_RETRY_GRID_PRESET = int(os.getenv("LLM_RETRY_GRID_PRESET", 3))
LLM_RETRY_FORM_SUGGESTION = int(os.getenv("LLM_RETRY_FORM_SUGGESTION", 3))
LLM_DELAY = int(os.getenv("LLM_DELAY", 0))
GRID_END_ADJUSTMENT_MAX_SECONDS = int(os.getenv("GRID_END_ADJUSTMENT_MAX_SECONDS", 15 * 60))

# Depassement de la fin de journee (editorial line end_at) par le playout flexible
# strict: aucun item ne doit finir apres la borne; soft: accepte tant que l'item commence avant la borne
FLEXIBLE_PLAYOUT_OVERFLOW_MODE = os.getenv("FLEXIBLE_PLAYOUT_OVERFLOW_MODE", "strict")

# Generation d'images (logos de chaines): "comfyui" (GPU local) ou "openai" (API cloud)
IMAGE_GENERATION_BACKEND = os.getenv("IMAGE_GENERATION_BACKEND", "comfyui")
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_WORKFLOW_TEMPLATE = os.getenv(
    "COMFYUI_WORKFLOW_TEMPLATE",
    str(BASE_DIR / "templates" / "tv_channel" / "comfyui" / "logo_workflow.json.j2"),
)
COMFYUI_TIMEOUT_SECONDS = int(os.getenv("COMFYUI_TIMEOUT_SECONDS", "300"))
OPENAI_IMAGE_API_KEY = os.getenv("OPENAI_IMAGE_API_KEY")
OPENAI_IMAGE_URL = os.getenv("OPENAI_IMAGE_URL")  # None = API OpenAI officielle
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")


GREEDY_MODE_NATURES = True
GREEDY_MODE_KINDS = True
GREEDY_MODE_CATEGORIES = True

DASHBOARD_STALE_SOURCE_DAYS = 7
