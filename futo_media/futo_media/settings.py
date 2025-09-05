# futo_media/settings.py
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Load local .env in development (safe fallback)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------
# Basic / Security
# -----------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ALLOWED_HOSTS: read comma-separated list from env var, else localhost defaults.
# Example: "localhost,127.0.0.1,futo-campus-media-backend.onrender.com"
raw_allowed = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in raw_allowed.split(",") if h.strip()]

# If running on Render, Render provides RENDER_EXTERNAL_HOSTNAME environment variable.
# Add it automatically if present and not already in the list.
render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)

# safe default for local development if nothing set
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# -----------------------
# Installed apps & middleware
# -----------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",

    # Cloudinary storage if used
    "cloudinary",
    "cloudinary_storage",

    # local apps
    "blog",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be high
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve static files efficiently
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "futo_media.wsgi.application"
ASGI_APPLICATION = "futo_media.asgi.application"

# -----------------------
# Database
# -----------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

# -----------------------
# Password validators
# -----------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------
# Internationalization
# -----------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# -----------------------
# Static files (WhiteNoise)
# -----------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise compression (optional)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# -----------------------
# -----------------------
# Cloudinary / Media
# -----------------------
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Check if all required Cloudinary credentials are provided
if all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    import cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    # Fallback to local filesystem if Cloudinary credentials are missing
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------
# CORS / CSRF
# -----------------------
# CORS_ALLOWED_ORIGINS can be a CSV env var: e.g. "https://futo-campus-media-frontend.onrender.com,http://localhost:5173"
raw_cors = os.getenv("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [u.strip() for u in raw_cors.split(",") if u.strip()]
# quick fallback - allow local dev front
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

# CSRF trusted origins (for secure deployments on https)
raw_csrf = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [u.strip() for u in raw_csrf.split(",") if u.strip()]
# If FRONTEND origin provided, add as trusted origin automatically
frontend_origin = os.getenv("VITE_API_CLIENT_ORIGIN")
if frontend_origin and frontend_origin not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(frontend_origin)

# -----------------------
# REST Framework
# -----------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------
# Security when behind a proxy (Render)
# -----------------------
# Render (and many platforms) terminates TLS and forwards X-Forwarded-* headers.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# If you want additional HTTPS settings, set them via env vars (optional)
if os.getenv("SECURE_HSTS_SECONDS"):
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() in ("true", "1", "yes")
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False").lower() in ("true", "1", "yes")
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() in ("true", "1", "yes")

# -----------------------
# Logging (simple)
# -----------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(levelname)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}

