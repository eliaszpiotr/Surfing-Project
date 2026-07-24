"""
Production settings profile for Surfing Project.

Use with:
    DJANGO_SETTINGS_MODULE=surfingproject.production_settings

This module is intentionally fail-closed. Missing security-critical
environment variables raise ImproperlyConfigured during startup.
"""

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403


def _require_env_value(name):
    """Return a non-empty environment value or fail startup."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is required in production.")
    return value


def _require_env_list(name):
    """Return a non-empty comma-separated environment list or fail startup."""
    values = env_list(name)
    if not values:
        raise ImproperlyConfigured(f"{name} must contain at least one value in production.")
    return values


def _reject_wildcard_hosts(hosts):
    """Reject host wildcards in production ALLOWED_HOSTS."""
    if any(host == "*" for host in hosts):
        raise ImproperlyConfigured("ALLOWED_HOSTS cannot contain '*' in production.")


def _reject_insecure_csrf_origins(origins):
    """Require HTTPS CSRF trusted origins in production."""
    insecure = [origin for origin in origins if not origin.startswith("https://")]
    if insecure:
        raise ImproperlyConfigured(
            "CSRF_TRUSTED_ORIGINS must use https:// origins in production."
        )


SECRET_KEY = _require_env_value("SECRET_KEY")
DEBUG = False

ALLOWED_HOSTS = _require_env_list("ALLOWED_HOSTS")
_reject_wildcard_hosts(ALLOWED_HOSTS)

CSRF_TRUSTED_ORIGINS = _require_env_list("CSRF_TRUSTED_ORIGINS")
_reject_insecure_csrf_origins(CSRF_TRUSTED_ORIGINS)

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True")
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", "True")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SERVE_MEDIA_LOCALLY = False

if SECURE_HSTS_SECONDS <= 0:
    raise ImproperlyConfigured("SECURE_HSTS_SECONDS must be positive in production.")
