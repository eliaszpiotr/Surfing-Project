import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_admin_rate_limit_cache():
    cache.clear()
    yield
    cache.clear()


def create_user(email, username, **extra_fields):
    return User.objects.create_user(
        email=email,
        username=username,
        password="pass1234",
        **extra_fields,
    )


@pytest.mark.django_db
def test_regular_user_cannot_access_admin_index(client):
    user = create_user("regular-admin@test.com", "regularadmin")
    client.force_login(user)

    response = client.get(reverse("admin:index"), follow=False)

    assert response.status_code == 302
    assert reverse("admin:login") in response.headers["Location"]


@pytest.mark.django_db
def test_staff_user_can_access_admin_index(client):
    staff = create_user(
        "staff-admin@test.com",
        "staffadmin",
        is_staff=True,
        is_superuser=True,
    )
    client.force_login(staff)

    response = client.get(reverse("admin:index"), follow=False)

    assert response.status_code == 200


@override_settings(ADMIN_ALLOWED_IPS=["203.0.113.10"])
def test_admin_ip_allowlist_blocks_untrusted_ip(client):
    response = client.get(reverse("admin:login"), REMOTE_ADDR="198.51.100.20")

    assert response.status_code == 403


@override_settings(ADMIN_ALLOWED_IPS=["203.0.113.10"])
def test_admin_ip_allowlist_allows_trusted_ip(client):
    response = client.get(reverse("admin:login"), REMOTE_ADDR="203.0.113.10")

    assert response.status_code == 200


@override_settings(
    RATE_LIMITS={
        "admin_login_ip": {"limit": 2, "window": 60},
        "admin_login_account": {"limit": 20, "window": 60},
    }
)
@pytest.mark.django_db
def test_admin_login_is_rate_limited_by_ip(client):
    url = reverse("admin:login")
    for _ in range(2):
        response = client.post(
            url,
            {"username": "admin@example.com", "password": "wrong"},
            REMOTE_ADDR="203.0.113.7",
        )
        assert response.status_code == 200

    response = client.post(
        url,
        {"username": "admin@example.com", "password": "wrong"},
        REMOTE_ADDR="203.0.113.7",
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
