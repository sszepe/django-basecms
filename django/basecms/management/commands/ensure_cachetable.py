"""
ensure_cachetable — idempotent wrapper around Django's createcachetable.

Run this once after migrate in production. Safe to run repeatedly.
The entrypoint command in docker-compose calls it before starting gunicorn.
"""
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = "Create the database cache table if it does not already exist."

    def handle(self, *args, **options):
        cache_backend = settings.CACHES.get("default", {}).get("BACKEND", "")
        if "DatabaseCache" not in cache_backend:
            self.stdout.write(
                self.style.NOTICE(
                    "Cache backend is not DatabaseCache — skipping createcachetable."
                )
            )
            return

        try:
            call_command("createcachetable", verbosity=0)
            self.stdout.write(self.style.SUCCESS("Cache table ready."))
        except Exception as exc:
            # Table already exists in some DB backends raises ProgrammingError
            if "already exists" in str(exc).lower():
                self.stdout.write(self.style.NOTICE("Cache table already exists."))
            else:
                raise
