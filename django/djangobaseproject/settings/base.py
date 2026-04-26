"""
base.py — shared settings inherited by every environment.

Rules:
  - No secrets, no DEBUG flags, no environment-specific paths here.
  - Every value that differs between envs is defined in local.py / production.py.
  - Import helpers live at the top so submodules don't repeat them.
"""
from pathlib import Path
import os

# Project root  (settings/base.py → settings/ → djangobaseproject/ → project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Language / localisation
# ---------------------------------------------------------------------------

def _parse_languages(raw: str) -> list[tuple[str, str]]:
    """Parse "en:English,de:German" from an env var into Django LANGUAGES format."""
    result = []
    for entry in (x.strip() for x in raw.split(",") if x.strip()):
        if ":" in entry:
            code, name = entry.split(":", 1)
        else:
            code, name = entry, entry.upper()
        result.append((code.strip(), name.strip()))
    return result


AVAILABLE_LANGUAGES = _parse_languages(
    os.getenv("CMS_AVAILABLE_LANGUAGES", "en:English,de:German")
)
LANGUAGE_CODE = AVAILABLE_LANGUAGES[0][0] if AVAILABLE_LANGUAGES else "en"
LANGUAGES = AVAILABLE_LANGUAGES
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
SITE_ID = 1

# ---------------------------------------------------------------------------
# Public-page rendering mode
# ---------------------------------------------------------------------------
#
# SERVE_PUBLIC_PAGES controls how CMS pages are rendered for site visitors.
#
#   "django"   — Django renders each page server-side using Django templates
#                (basecms/page.html + block templates).
#                No React dependency at runtime; works without a Vite build.
#                Good for: simple deployments, SEO-critical sites, no JS SPA.
#
#   "frontend" — Django serves a thin React shell (basecms/react_site.html)
#                and injects __SITE_CONFIG__. The React SPA fetches page data
#                from the public JSON API (/<lang>/<slug>/data/) and renders
#                blocks client-side using the block components in src/public/.
#                Good for: rich interactivity, consistent look with the cockpit,
#                projects where the frontend build is always available.
#
# Set via environment variable CMS_SERVE_PUBLIC_PAGES.
# Validated at startup — raises ImproperlyConfigured for unknown values.

_SERVE_PUBLIC_PAGES_RAW = os.getenv("CMS_SERVE_PUBLIC_PAGES", "django").strip().lower()

_VALID_SERVE_MODES = {"django", "frontend"}
if _SERVE_PUBLIC_PAGES_RAW not in _VALID_SERVE_MODES:
    # Deferred import avoids circular issues at module load time
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        f"CMS_SERVE_PUBLIC_PAGES={_SERVE_PUBLIC_PAGES_RAW!r} is not valid. "
        f"Choose one of: {sorted(_VALID_SERVE_MODES)}"
    )

SERVE_PUBLIC_PAGES: str = _SERVE_PUBLIC_PAGES_RAW

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "rest_framework",
    "drf_spectacular",
    "guardian",
    "django_q",
    "basecms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    # "basecms.middleware.CMSRedirectMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "djangobaseproject.urls"
WSGI_APPLICATION = "djangobaseproject.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "basecms.context_processors.navbar_context",
            ],
        },
    }
]

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]
ANONYMOUS_USER_NAME = "anonymous"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# Static & media  (URLs only — roots are set per-environment)
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# ---------------------------------------------------------------------------
# Django Q2  (async task queue, ORM broker — no Redis dependency)
# ---------------------------------------------------------------------------

Q_CLUSTER = {
    "name": "basecms",
    "workers": int(os.getenv("Q_WORKERS", "2")),
    "recycle": 500,
    "timeout": 60,
    "compress": True,
    "save_limit": 250,
    "queue_limit": 500,
    "cpu_affinity": 1,
    "label": "basecms Tasks",
    "orm": "default",
}

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "60/minute"),
        "user": os.getenv("THROTTLE_USER", "300/minute"),
    },
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI)
# ---------------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "basecms API",
    "DESCRIPTION": "Standalone CMS API for pages, blocks, media, and navigation.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "filter": True,
        "tryItOutEnabled": True,
    },
    "REDOC_UI_SETTINGS": {
        "hideDownloadButton": False,
        "scrollYOffset": 60,
    },
}

# ---------------------------------------------------------------------------
# CMS
# ---------------------------------------------------------------------------

CMS_REDIRECT_EXCLUDE_PATHS = [
    "/admin/",
    "/api/",
    "/accounts/",
    "/static/",
    "/media/",
    "/cockpit/",    # React SPA — served by nginx (matches with and without trailing slash)
]
