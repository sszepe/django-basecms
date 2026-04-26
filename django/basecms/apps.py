from django.apps import AppConfig


class BasecmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "basecms"

    def ready(self):
        from . import signals  # noqa: F401 — cache invalidation signals

        # Job signals are optional: only wire up when django_q is installed.
        try:
            import django_q  # noqa: F401
            from . import signals_jobs  # noqa: F401
        except ImportError:
            pass
