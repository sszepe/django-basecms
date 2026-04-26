"""
production.py — production settings.

Usage:
    DJANGO_SETTINGS_MODULE=djangobaseproject.settings.production

Requirements (all via environment variables — no secrets in code):
    DJANGO_SECRET_KEY     — long random string, required
    POSTGRES_HOST         — required
    POSTGRES_DB           — default: basecms
    POSTGRES_USER         — default: basecms
    POSTGRES_PASSWORD     — required
    ALLOWED_HOSTS         — comma-separated, e.g. "example.com,www.example.com"
    CSRF_TRUSTED_ORIGINS  — comma-separated full origins

Characteristics:
  - PostgreSQL database with persistent connections
  - Django database cache (cachetable) — zero extra services, nginx-compatible
  - DEBUG = False with full security header suite
  - Static files and media served by nginx (Django never touches them at runtime)
  - collectstatic writes to STATIC_ROOT; nginx reads from the same volume
  - django-q ORM broker (uses the same DB connection pool, no Redis needed)
"""
from .base import *  # noqa: F401, F403
import os


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Check your .env file or container environment."
        )
    return value


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = _require_env("DJANGO_SECRET_KEY")

# "django"   → Django template rendering
# "frontend" → React SPA shell (Vite build must be present)
SERVE_PUBLIC_PAGES = os.getenv("CMS_SERVE_PUBLIC_PAGES", "frontend")
DEBUG = False

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "").split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    h.strip()
    for h in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if h.strip()
]

# ---------------------------------------------------------------------------
# Database — PostgreSQL with connection pooling
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "basecms"),
        "USER": os.getenv("POSTGRES_USER", "basecms"),
        "PASSWORD": _require_env("POSTGRES_PASSWORD"),
        "HOST": _require_env("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        "OPTIONS": {
            "connect_timeout": 10,
        },
        "TEST": {
            "NAME": os.getenv("POSTGRES_TEST_DB", "basecms_test"),
        },
    }
}

# ---------------------------------------------------------------------------
# Cache — Django database cache (cachetable)
#
# No Redis, no Memcached. The cache table is created once with:
#     python manage.py createcachetable
# It is included in the standard `migrate` command via management/commands.
# Suitable for low-to-medium traffic; swap to Redis with a one-line change
# if you later need distributed caching.
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "basecms_cache",         # table name
        "TIMEOUT": int(os.getenv("CACHE_TIMEOUT", "300")),
        "OPTIONS": {
            "MAX_ENTRIES": int(os.getenv("CACHE_MAX_ENTRIES", "1000")),
            "CULL_FREQUENCY": 3,             # delete 1/3 of entries when full
        },
        "KEY_PREFIX": "basecms",
    }
}

# ---------------------------------------------------------------------------
# Static & media
#
# nginx serves both /static/ and /media/ directly from mounted Docker volumes.
# Django's collectstatic writes to STATIC_ROOT at build/deploy time.
# At runtime Django never serves a single static or media file.
# ---------------------------------------------------------------------------

STATIC_ROOT = BASE_DIR / "static"   # noqa: F405  — nginx volume mount point
MEDIA_ROOT = BASE_DIR / "media"     # noqa: F405  — nginx volume mount point

# No STATICFILES_STORAGE override needed: Django's default ManifestStaticFilesStorage
# hashes filenames for cache-busting; nginx handles the serving.
# Plain storage — admin static files use exact names; Vite handles JS/CSS cache-busting
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

SECURE_HSTS_SECONDS = int(os.getenv("HSTS_SECONDS", "31536000"))   # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Set to True only when nginx terminates TLS and proxies to Django over HTTP.
# nginx should also set: proxy_set_header X-Forwarded-Proto https
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "false").lower() == "true"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False   # React cockpit reads the CSRF cookie via JS
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "strict-origin-when-cross-origin"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)

# ---------------------------------------------------------------------------
# Logging — structured, production-safe
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "mail_admins"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "basecms": {
            "handlers": ["console"],
            "level": os.getenv("APP_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Admin security
# ---------------------------------------------------------------------------

ADMINS = [
    (name.strip(), email.strip())
    for entry in os.getenv("DJANGO_ADMINS", "").split(";")
    if "," in entry
    for name, email in [entry.split(",", 1)]
]