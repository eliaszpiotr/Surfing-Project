from datetime import timedelta
import importlib

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.base import ContentFile
from django.urls import clear_url_caches
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings

import surfingproject.urls as project_urls
from spots.models import Spot, SpotPhoto
from surf_sessions.models import Session

User = get_user_model()


def create_user(email, username):
    """Create a user for home-page session fixtures."""
    return User.objects.create_user(email=email, username=username, password="pass1234")


@pytest.mark.django_db
def test_home_lists_only_ten_future_sessions_sorted(client):
    organizer = create_user("home@test.com", "homeuser")
    spot = Spot.objects.create(
        name="Ericeira",
        author=organizer,
        country="PT",
        latitude=38.966,
        longitude=-9.417,
    )
    today = timezone.localdate()

    created_names = []
    for offset in range(12):
        session = Session.objects.create(
            name=f"Session {offset}",
            spot=spot,
            organizer=organizer,
            date=today + timedelta(days=offset),
            start_time="08:00",
        )
        created_names.append(session.name)

    Session.objects.create(
        name="Past session",
        spot=spot,
        organizer=organizer,
        date=today - timedelta(days=1),
        start_time="08:00",
    )

    response = client.get(reverse("home"))

    assert response.status_code == 200
    sessions = list(response.context["upcoming_sessions"])
    assert len(sessions) == 10
    assert [session.name for session in sessions] == created_names[:10]
    assert all(session.date >= today for session in sessions)


@pytest.mark.django_db
def test_home_allows_anonymous_access(client):
    response = client.get(reverse("home"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_home_links_session_organizer_to_public_profile(client):
    organizer = create_user("link-home@test.com", "linkhome")
    spot = Spot.objects.create(
        name="Hossegor",
        author=organizer,
        country="FR",
        latitude=43.665,
        longitude=-1.444,
    )
    Session.objects.create(
        name="Evening surf",
        spot=spot,
        organizer=organizer,
        date=timezone.localdate() + timedelta(days=1),
        start_time="18:00",
    )
    client.force_login(organizer)

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert reverse("accounts:user_profile", args=[organizer.username]) in response.content.decode()


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_seed_demo_rebuilds_missing_media_files():
    call_command("seed_demo")

    user = User.objects.get(username="anna")
    photo = SpotPhoto.objects.get(caption="Cold sunrise lines")

    assert user.profile.profile_picture.storage.exists(user.profile.profile_picture.name)
    assert photo.image.storage.exists(photo.image.name)

    user.profile.profile_picture.storage.delete(user.profile.profile_picture.name)
    photo.image.storage.delete(photo.image.name)

    assert not user.profile.profile_picture.storage.exists(user.profile.profile_picture.name)
    assert not photo.image.storage.exists(photo.image.name)

    call_command("seed_demo")

    user.profile.refresh_from_db()
    photo.refresh_from_db()

    assert user.profile.profile_picture.storage.exists(user.profile.profile_picture.name)
    assert photo.image.storage.exists(photo.image.name)


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_seed_demo_is_blocked_when_debug_is_false():
    with pytest.raises(CommandError, match="seed_demo can only run when DEBUG=True"):
        call_command("seed_demo")


@pytest.mark.django_db
@override_settings(DEBUG=False, SERVE_MEDIA_LOCALLY=True)
def test_media_is_served_when_debug_is_false_and_local_media_is_enabled(client):
    clear_url_caches()
    importlib.reload(project_urls)

    user = create_user("media@test.com", "mediauser")
    spot = Spot.objects.create(
        name="Cold Hawaii",
        author=user,
        country="DK",
        latitude=56.956,
        longitude=8.694,
    )
    photo = SpotPhoto.objects.create(
        spot=spot,
        author=user,
        caption="Grey lines",
        image=ContentFile(b"fake image bytes", name="grey-lines.jpg"),
    )

    response = client.get(photo.image.url)

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"fake image bytes"
