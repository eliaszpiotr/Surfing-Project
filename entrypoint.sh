#!/bin/sh
set -eu

if [ -z "${SECRET_KEY:-}" ]; then
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
  python manage.py seed_demo
fi

exec "$@"
