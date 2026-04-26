#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# init-db/01-init-user.sh
#
# Idempotent: creates the application role and database if they don't exist.
# Runs automatically when the postgres container starts with an empty data dir.
# Mounted at: ./init-db:/docker-entrypoint-initdb.d
#
# The POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB env vars are already
# set by docker-compose from your .env file, so we just reference them here.
# ─────────────────────────────────────────────────────────────────────────────
set -e

# The superuser is "postgres" — use it to create the app role
psql -v ON_ERROR_STOP=1 --username "postgres" << SQL

-- Create the application role (idempotent)
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${POSTGRES_USER}') THEN
    CREATE ROLE "${POSTGRES_USER}" LOGIN PASSWORD '${POSTGRES_PASSWORD}';
    RAISE NOTICE 'Role "${POSTGRES_USER}" created.';
  ELSE
    -- Update password in case it changed
    ALTER ROLE "${POSTGRES_USER}" LOGIN PASSWORD '${POSTGRES_PASSWORD}';
    RAISE NOTICE 'Role "${POSTGRES_USER}" already exists — password updated.';
  END IF;
END
\$\$;

-- Create the application database (idempotent)
SELECT 'CREATE DATABASE "${POSTGRES_DB}" OWNER "${POSTGRES_USER}"'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB}')
\gexec

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE "${POSTGRES_DB}" TO "${POSTGRES_USER}";

SQL

echo "[init-db] Role '${POSTGRES_USER}' and database '${POSTGRES_DB}' are ready."
