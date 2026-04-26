"""
local.py — development settings.

Usage:
    export DJANGO_SETTINGS_MODULE=djangobaseproject.settings.local
    python manage.py runserver

Or simply run `manage.py` — it defaults to this module.

Characteristics:
  - SQLite database (zero setup)
  - Django's in-memory cache (locmem)
  - DEBUG = True, all hosts allowed
  - No security headers
  - Django dev server serves /static/ and /media/ directly
  - django-q ORM broker (no external services needed)
"""
from .base import *  # noqa: F401, F403
import os

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-dev-secret-key-not-for-production")

# "django"   → Django template rendering (no Vite build needed)
# "frontend" → React SPA shell (requires npm run build or Vite dev server)
SERVE_PUBLIC_PAGES = os.getenv("CMS_SERVE_PUBLIC_PAGES", "django")
DEBUG = True
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# ---------------------------------------------------------------------------
# Database — SQLite, no setup required
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# ---------------------------------------------------------------------------
# Cache — in-process locmem, resets on every runserver restart
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "basecms-local",
    }
}

# ---------------------------------------------------------------------------
# Static & media — served by Django's dev server via urls.py
# ---------------------------------------------------------------------------

STATIC_ROOT = BASE_DIR / "static"   # noqa: F405
MEDIA_ROOT  = BASE_DIR / "media"    # noqa: F405

# Vite dev server port — used by cms_react_tags in DEBUG mode
VITE_DEV_PORT = 5173

# ---------------------------------------------------------------------------
# Email — print to console
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Development extras
# ---------------------------------------------------------------------------

# Show all queries in the shell via: from django.db import connection; connection.queries
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "basecms": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
