import re

from django.http import HttpResponseBadRequest


# Path traversal patterns — raw and URL-encoded variants
_TRAVERSAL_RE = re.compile(
    r"\.\./|\.\.\\|"           # ../  ..\
    r"%2e%2e[%2f%5c]|"         # URL-encoded: %2e%2e%2f  %2e%2e%5c
    r"%252e%252e|"             # double-encoded: %252e%252e
    r"\.{2,}[/\\]",            # ../../  or  ..\..\
    re.IGNORECASE,
)

_NULL_BYTE_RE = re.compile(r"%00|\x00")  # null byte injection

# Content-Security-Policy directive breakdown:
#   script-src   — own static files + Bootstrap (jsdelivr) + Leaflet/markercluster (unpkg)
#                  NO 'unsafe-inline': all JS is in static files
#   style-src    — 'unsafe-inline' is required because the templates use inline <style> blocks
#                  (map heights, etc.) and style="" attributes throughout; moving all of them
#                  to external CSS files is out of scope here.  'unsafe-inline' for styles is
#                  far less dangerous than for scripts (no code execution possible via CSS alone).
#   img-src      — own files, OpenStreetMap tiles, data URIs (profile avatars)
#   connect-src  — own origin only (AJAX load-more, map data fetch)
#   object-src   — 'none': block Flash and legacy plugins
#   base-uri / form-action — restrict to own origin to prevent injection attacks
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
    "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)


class PathSecurityMiddleware:
    """Rejects requests that contain path traversal sequences or null bytes in the URL."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Return 400 if the request path contains a traversal or null-byte pattern."""
        full_path = request.get_full_path()

        if _TRAVERSAL_RE.search(full_path):
            return HttpResponseBadRequest("Invalid path.")

        if _NULL_BYTE_RE.search(full_path):
            return HttpResponseBadRequest("Invalid path.")

        return self.get_response(request)


class SecurityHeadersMiddleware:
    """Adds security headers (CSP, Permissions-Policy, CORP, COOP) to every HTTP response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Attach security headers; uses setdefault so individual views can override them."""
        response = self.get_response(request)

        response.setdefault("Content-Security-Policy", _CSP)
        response.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")

        return response
