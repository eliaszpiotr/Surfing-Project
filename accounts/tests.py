import io
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import UserProfile
from spots.models import Spot
from surf_sessions.models import Session

User = get_user_model()


def create_user(email, username):
    """Create a basic user for account tests."""
    return User.objects.create_user(email=email, username=username, password="pass1234")


def create_spot(author, name="Peniche"):
    """Create a reusable spot for profile/session tests."""
    return Spot.objects.create(name=name, author=author, country="PT", latitude=39.355, longitude=-9.381)


def make_profile_image(name="avatar.jpg", fmt="JPEG"):
    """Create a valid in-memory profile image for upload tests."""
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color="teal").save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


@pytest.mark.django_db
def test_register_creates_user_profile_and_logs_user_in(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "email": "newuser@test.com",
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "password1": "StrongPass123",
            "password2": "StrongPass123",
        },
        follow=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("accounts:profile_settings")

    user = User.objects.get(email="newuser@test.com")
    assert UserProfile.objects.filter(user=user).exists()
    assert str(client.session["_auth_user_id"]) == str(user.pk)


@pytest.mark.django_db
def test_register_invalid_data_does_not_create_user(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "email": "baduser@test.com",
            "username": "baduser",
            "password1": "StrongPass123",
            "password2": "DifferentPass123",
        },
        follow=False,
    )

    assert response.status_code == 200
    assert not User.objects.filter(email="baduser@test.com").exists()


@pytest.mark.django_db
def test_login_redirects_to_safe_next_from_post_data(client):
    user = create_user("login@test.com", "loginuser")

    response = client.post(
        reverse("accounts:login"),
        {
            "username": user.email,
            "password": "pass1234",
            "next": reverse("accounts:profile"),
        },
        follow=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("accounts:profile")


@pytest.mark.django_db
def test_login_rejects_unsafe_next_and_falls_back_home(client):
    user = create_user("unsafe@test.com", "unsafeuser")

    response = client.post(
        reverse("accounts:login"),
        {
            "username": user.email,
            "password": "pass1234",
            "next": "https://evil.example/steal-session",
        },
        follow=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("home")


@pytest.mark.django_db
def test_logout_post_logs_user_out(client):
    user = create_user("logout@test.com", "logoutuser")
    client.force_login(user)

    response = client.post(reverse("accounts:logout"), follow=False)

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("home")
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_profile_requires_login(client):
    response = client.get(reverse("accounts:profile"), follow=False)

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]


@pytest.mark.django_db
def test_profile_splits_upcoming_and_history_sessions(client):
    user = create_user("profile@test.com", "profileuser")
    organizer = create_user("organizer@test.com", "organizer")
    spot = create_spot(organizer)
    today = timezone.localdate()

    upcoming = Session.objects.create(
        name="Future surf",
        spot=spot,
        organizer=organizer,
        date=today + timedelta(days=3),
        start_time="07:00",
    )
    past = Session.objects.create(
        name="Past surf",
        spot=spot,
        organizer=organizer,
        date=today - timedelta(days=3),
        start_time="07:00",
    )
    upcoming.participants.add(user)
    past.participants.add(user)

    client.force_login(user)
    response = client.get(reverse("accounts:profile"))

    assert response.status_code == 200
    assert list(response.context["upcoming_sessions"]) == [upcoming]
    assert list(response.context["history_sessions"]) == [past]


@pytest.mark.django_db
def test_profile_settings_requires_login(client):
    response = client.get(reverse("accounts:profile_settings"), follow=False)

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]


@pytest.mark.django_db
def test_profile_settings_updates_country_bio_and_picture(client):
    user = create_user("edit@test.com", "edituser")
    client.force_login(user)

    response = client.post(
        reverse("accounts:profile_settings"),
        {
            "country": "DK",
            "bio": "Cold-water surfer",
            "profile_picture": make_profile_image(),
        },
        follow=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("accounts:profile")

    user.refresh_from_db()
    assert str(user.profile.country) == "DK"
    assert user.profile.bio == "Cold-water surfer"
    assert user.profile.profile_picture.name.endswith(".jpg")


@pytest.mark.django_db
def test_profile_settings_rejects_invalid_image_upload(client):
    user = create_user("invalidpic@test.com", "invalidpic")
    client.force_login(user)

    response = client.post(
        reverse("accounts:profile_settings"),
        {
            "country": "DK",
            "bio": "Still testing",
            "profile_picture": SimpleUploadedFile("fake.jpg", b"not-an-image", content_type="image/jpeg"),
        },
        follow=False,
    )

    assert response.status_code == 200
    assert "profile_picture" in response.context["form"].errors
