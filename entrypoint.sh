#!/bin/sh
set -eu

DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-surfingproject.settings}"
export DJANGO_SETTINGS_MODULE

is_true() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

if [ -z "${SECRET_KEY:-}" ]; then
  if [ "$DJANGO_SETTINGS_MODULE" = "surfingproject.production_settings" ]; then
    echo "SECRET_KEY is required when using surfingproject.production_settings." >&2
    exit 1
  fi

  export SECRET_KEY="$(python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
)"
fi

if [ "${DB_ENGINE:-postgresql}" = "postgresql" ]; then
  python - <<'PY'
import os
import time

import psycopg2

host = os.environ.get("DB_HOST", "db")
port = os.environ.get("DB_PORT", "5432")
name = os.environ.get("DB_NAME", "surfing")
user = os.environ.get("DB_USER", "surfing")
password = os.environ.get("DB_PASSWORD", "surfing")

for attempt in range(30):
    try:
        conn = psycopg2.connect(
            dbname=name,
            user=user,
            password=password,
            host=host,
            port=port,
        )
        conn.close()
        break
    except psycopg2.OperationalError:
        time.sleep(1)
else:
    raise SystemExit("Database is not ready after 30 seconds.")
PY
fi

python manage.py migrate --noinput

if [ "${RUN_COLLECTSTATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

if [ "${RUN_DEMO_SEED:-0}" = "1" ]; then
  if ! is_true "${DEBUG:-False}"; then
    echo "RUN_DEMO_SEED is only allowed when DEBUG=True." >&2
    exit 1
  fi
  python manage.py seed_demo
fi

exec "$@"
