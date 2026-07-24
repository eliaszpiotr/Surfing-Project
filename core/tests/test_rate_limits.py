import pytest
from django.core.cache import cache
from django.test import override_settings

from surfingproject.rate_limits import (
    client_ip_identifier,
    get_client_ip,
    is_rate_limited,
)


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    cache.clear()
    yield
    cache.clear()


def test_rate_limit_allows_until_limit_then_blocks():
    assert is_rate_limited("test", "client", limit=2, window=60) is False
    assert is_rate_limited("test", "client", limit=2, window=60) is False
    assert is_rate_limited("test", "client", limit=2, window=60) is True


def test_rate_limit_keys_are_scoped_by_identifier():
    assert is_rate_limited("test", "client-a", limit=1, window=60) is False
    assert is_rate_limited("test", "client-b", limit=1, window=60) is False
    assert is_rate_limited("test", "client-a", limit=1, window=60) is True


def test_client_ip_does_not_trust_forwarded_for_by_default(rf):
    request = rf.get(
        "/",
        HTTP_X_FORWARDED_FOR="203.0.113.10, 10.0.0.1",
        REMOTE_ADDR="198.51.100.20",
    )

    assert get_client_ip(request) == "198.51.100.20"


@override_settings(TRUST_PROXY_HEADERS=True)
def test_client_ip_can_trust_forwarded_for_when_enabled(rf):
    request = rf.get(
        "/",
        HTTP_X_FORWARDED_FOR="203.0.113.10, 10.0.0.1",
        REMOTE_ADDR="198.51.100.20",
    )

    assert get_client_ip(request) == "203.0.113.10"


def test_client_ip_identifier_hashes_raw_ip(rf):
    request = rf.get("/", REMOTE_ADDR="198.51.100.20")

    assert client_ip_identifier(request).startswith("ip:")
    assert "198.51.100.20" not in client_ip_identifier(request)
