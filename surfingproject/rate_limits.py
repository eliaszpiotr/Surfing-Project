import hashlib

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


TOO_MANY_REQUESTS_MESSAGE = "Too many requests. Please try again later."


def _hash_identifier(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def get_client_ip(request):
    """Return the client IP without trusting proxy headers unless explicitly enabled."""
    if getattr(settings, "TRUST_PROXY_HEADERS", False):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()

    return request.META.get("REMOTE_ADDR", "unknown")


def client_ip_identifier(request):
    return f"ip:{_hash_identifier(get_client_ip(request))}"


def user_or_ip_identifier(request):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return client_ip_identifier(request)


def posted_value_identifier(request, field_name):
    value = request.POST.get(field_name, "").strip().lower()
    if not value:
        return "empty"
    return _hash_identifier(value)


def get_rate_limit(name):
    rule = settings.RATE_LIMITS[name]
    return int(rule["limit"]), int(rule["window"])


def is_rate_limited(namespace, identifier, limit, window):
    if limit <= 0 or window <= 0:
        return False

    key = f"rl:{namespace}:{identifier}"
    if cache.add(key, 1, timeout=window):
        return False

    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        return False

    return count > limit


def rate_limited_response(request, name, identifier):
    limit, window = get_rate_limit(name)
    if not is_rate_limited(name, identifier, limit, window):
        return None

    response = HttpResponse(TOO_MANY_REQUESTS_MESSAGE, status=429)
    response["Retry-After"] = str(window)
    return response
