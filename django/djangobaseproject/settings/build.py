"""
build.py — settings used exclusively during `docker build` (collectstatic stage).

This module is intentionally minimal:
  - Inherits shared app/template/static config from base.py
  - Uses SQLite so no database connection is attempted
  - Accepts a dummy SECRET_KEY so Django starts without env vars
  - Never used at runtime — only referenced in the Dockerfile RUN step

DJANGO_SETTINGS_MODULE=djangobaseproject.settings.build
"""
from .base import *  # noqa: F401, F403
import os

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "build-only-placeholder-not-used-at-runtime")
DEBUG = False
ALLOWED_HOSTS = ["*"]
SERVE_PUBLIC_PAGES = "django"

# SQLite — no POSTGRES_HOST needed, DB is never accessed during collectstatic
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/tmp/build.sqlite3",
    }
}

# Suppress cache table requirement during build
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

STATIC_ROOT = BASE_DIR / "static"   # noqa: F405
MEDIA_ROOT  = BASE_DIR / "media"    # noqa: F405

# Standard (non-manifest) storage for the build step — ManifestStaticFilesStorage
# requires the DB for its post_process step when strict=True in some configs.
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
