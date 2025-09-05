# futo_media/settings.py
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Load .env from project root (if present)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------
# Basic / Security
# -------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# ALLOWED_HOSTS: comma-separated in env, fallback to localhosts
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# -------------------------
# Installed apps
# -------------------------
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",

    # Cloudinary (optional)
    "cloudinary",
    "cloudinary_storage",

    # Local apps
    "blog",
]

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must come early
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve static files on Render/simple hosts
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "futo_media.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # add template dirs if needed
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # useful for request.build_absolute_uri()
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "futo_media.wsgi.application"
ASGI_APPLICATION = "futo_media.asgi.application"

# -------------------------
# Database (DATABASE_URL recommended on Render)
# -------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

# -------------------------
# Password validation
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------
# Internationalization & timezone
# -------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# -------------------------
# Static files (CSS, JS, images)
# -------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise compressed manifest storage (recommended on Render)
STATICFILES_STORAGE = os.getenv(
    "STATICFILES_STORAGE", "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

# Optionally include local static dir(s)
STATICFILES_DIRS = [
    # BASE_DIR / "static",
]

# -------------------------
# Media & Cloudinary
# -------------------------
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
FORCE_CLOUDINARY = os.getenv("FORCE_CLOUDINARY", "False").lower() in ("true", "1", "yes")

USE_CLOUDINARY = False
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    USE_CLOUDINARY = True
elif FORCE_CLOUDINARY:
    # If forced but creds are missing, uploads will fail. Prefer to set the three CLOUDINARY_* vars.
    USE_CLOUDINARY = True

if USE_CLOUDINARY:
    # Configure Cloudinary SDK and use Cloudinary storage for media
    import cloudinary

    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "API_KEY": CLOUDINARY_API_KEY,
        "API_SECRET": CLOUDINARY_API_SECRET,
    }
else:
    # Local filesystem storage fallback (dev)
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Keep MEDIA_URL / MEDIA_ROOT for local dev and for compatibility
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -------------------------
# CORS & CSRF
# -------------------------
# Allow passing CORS origins via env:
vite_origin = os.getenv("VITE_API_CLIENT_ORIGIN")
env_cors = os.getenv("CORS_ALLOWED_ORIGINS", "")
if env_cors:
    CORS_ALLOWED_ORIGINS = [u.strip() for u in env_cors.split(",") if u.strip()]
elif vite_origin:
    CORS_ALLOWED_ORIGINS = [vite_origin]
else:
    CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

if os.getenv("CORS_ALLOW_ALL", "False").lower() in ("true", "1", "yes"):
    CORS_ALLOW_ALL_ORIGINS = True

# CSRF trusted origins: comma-separated env var (include frontend origin)
csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if csrf_env:
    CSRF_TRUSTED_ORIGINS = [u.strip() for u in csrf_env.split(",") if u.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [vite_origin] if vite_origin else []

# -------------------------
# Security settings (apply in production when DEBUG=False)
# -------------------------
# When behind a proxy (Render) accept the X-Forwarded-Proto header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1", "yes")
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() in ("true", "1", "yes")
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "True").lower() in ("true", "1", "yes")
else:
    # relaxed for local development
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False

# -------------------------
# REST framework
# -------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# -------------------------
# Misc / Defaults
# -------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------
# Logging (simple)
# -------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(levelname)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}
