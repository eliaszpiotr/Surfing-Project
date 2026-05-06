from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from spots.models import Spot
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
