# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: install deps + collectstatic
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

# Use the build-only settings module — no DB, no secrets needed
RUN DJANGO_SETTINGS_MODULE=djangobaseproject.settings.build \
    python manage.py collectstatic --noinput

# FIX: Store the Vite manifest at a path outside STATIC_ROOT so the volume
# mount at /app/static/ doesn't hide it at runtime. The startup command
# (in docker-compose.yml) copies it into /app/static/.vite/ after
# collectstatic populates the volume. This is the only reliable way to get
# the manifest into the volume without a race condition or a separate service.
RUN if [ -f frontend/dist/.vite/manifest.json ]; then \
        cp frontend/dist/.vite/manifest.json /app/manifest-vite.json && \
        echo "[build] Vite manifest saved to /app/manifest-vite.json"; \
    else \
        echo '{}' > /app/manifest-vite.json && \
        echo "[build] No frontend build found — saved empty manifest placeholder"; \
    fi

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY . .
# Copy the static dir and the pre-built Vite manifest from the builder stage
COPY --from=builder /app/static /app/static
COPY --from=builder /app/manifest-vite.json /app/manifest-vite.json

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/schema/ || exit 1

CMD ["gunicorn", "wsgi:application"]
