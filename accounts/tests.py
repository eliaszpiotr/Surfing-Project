import io
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import UserProfile
from spots.models import Spot, SpotPhoto
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
@override_settings(
    RATE_LIMITS={
        "login_ip": {"limit": 2, "window": 60},
        "login_account": {"limit": 20, "window": 60},
    }
)
def test_login_is_rate_limited_by_ip(client):
    user = create_user("limited@test.com", "limited")
    cache.clear()

    url = reverse("accounts:login")
    for _ in range(2):
        response = client.post(url, {"username": user.email, "password": "wrong"}, REMOTE_ADDR="203.0.113.7")
        assert response.status_code == 200

    response = client.post(url, {"username": user.email, "password": "wrong"}, REMOTE_ADDR="203.0.113.7")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    cache.clear()


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
def test_public_profile_is_accessible_by_username(client):
    user = create_user("public@test.com", "publicuser")
    user.first_name = "Public"
    user.last_name = "Surfer"
    user.save(update_fields=["first_name", "last_name"])

    response = client.get(reverse("accounts:user_profile", args=[user.username]))

    assert response.status_code == 200
    assert response.context["profile_user"] == user
    assert response.context["is_own_profile"] is False
    assert response.context["followers_count"] == 0
    assert response.context["following_count"] == 0


@pytest.mark.django_db
def test_profile_includes_user_uploaded_spot_photos(client):
    user = create_user("gallery@test.com", "galleryuser")
    spot = create_spot(user, name="Rincon")
    photo = SpotPhoto.objects.create(
        spot=spot,
        author=user,
        caption="Golden hour",
        image=make_profile_image(name="spot-photo.jpg"),
    )

    client.force_login(user)
    response = client.get(reverse("accounts:profile"))

    assert response.status_code == 200
    assert list(response.context["uploaded_spot_photos"]) == [photo]


@pytest.mark.django_db
def test_follow_toggle_creates_relationship_and_updates_counts(client):
    follower = create_user("follower@test.com", "follower")
    target = create_user("target@test.com", "target")
    client.force_login(follower)

    response = client.post(reverse("accounts:follow_toggle", args=[target.username]), follow=False)

    assert response.status_code == 302
    follower.refresh_from_db()
    target.refresh_from_db()
    assert follower.is_following(target) is True
    assert target.followers_count == 1
    assert follower.following_count == 1


@pytest.mark.django_db
def test_follow_toggle_second_post_unfollows_user(client):
    follower = create_user("double@test.com", "double")
    target = create_user("double-target@test.com", "doubletarget")
    follower.following.add(target)
    client.force_login(follower)

    response = client.post(reverse("accounts:follow_toggle", args=[target.username]), follow=False)

    assert response.status_code == 302
    follower.refresh_from_db()
    assert follower.is_following(target) is False


@pytest.mark.django_db
def test_public_profile_shows_unfollow_button_when_already_following(client):
    follower = create_user("viewfollow@test.com", "viewfollow")
    target = create_user("viewtarget@test.com", "viewtarget")
    follower.following.add(target)
    client.force_login(follower)

    response = client.get(reverse("accounts:user_profile", args=[target.username]))

    assert response.status_code == 200
    assert "Unfollow" in response.content.decode()
    assert ">Follow<" not in response.content.decode()


@pytest.mark.django_db
def test_follow_toggle_does_not_allow_following_self(client):
    user = create_user("self@test.com", "selfuser")
    client.force_login(user)

    response = client.post(reverse("accounts:follow_toggle", args=[user.username]), follow=False)

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.following_count == 0


@pytest.mark.django_db
@override_settings(
    RATE_LIMITS={
        "follow_user": {"limit": 1, "window": 60},
    }
)
def test_follow_toggle_is_rate_limited(client):
    follower = create_user("followlimit@test.com", "followlimit")
    first_target = create_user("firsttarget@test.com", "firsttarget")
    second_target = create_user("secondtarget@test.com", "secondtarget")
    cache.clear()
    client.force_login(follower)

    assert client.post(reverse("accounts:follow_toggle", args=[first_target.username])).status_code == 302
    response = client.post(reverse("accounts:follow_toggle", args=[second_target.username]))

    assert response.status_code == 429
    cache.clear()


@pytest.mark.django_db
def test_profile_settings_requires_login(client):
    response = client.get(reverse("accounts:profile_settings"), follow=False)

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]


@pytest.mark.django_db
def test_logout_is_not_shown_in_navbar_but_is_visible_on_own_profile(client):
    user = create_user("nav@test.com", "navuser")
    client.force_login(user)

    home_response = client.get(reverse("home"))
    profile_response = client.get(reverse("accounts:profile"))

    assert home_response.status_code == 200
    assert profile_response.status_code == 200
    assert "Logout" not in home_response.content.decode()
    assert "Logout" in profile_response.content.decode()


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
