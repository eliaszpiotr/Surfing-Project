from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from chat.models import Conversation, Message
from notifications.models import Notification
from spots.models import Spot
from surf_sessions.models import Session

User = get_user_model()


def create_user(email, username):
    return User.objects.create_user(email=email, username=username, password="pass1234")


def create_spot(author, name="Rincon"):
    return Spot.objects.create(
        name=name,
        author=author,
        country="US",
        latitude=35.0,
        longitude=-120.0,
    )


def create_session(organizer, participant=None, name="Morning session"):
    spot = create_spot(organizer, name=f"Spot for {name}")
    session = Session.objects.create(
        name=name,
        spot=spot,
        organizer=organizer,
        date=timezone.localdate() + timedelta(days=7),
        start_time="08:00",
        max_participants=5,
    )
    if participant:
        session.participants.add(participant)
    return session


@pytest.mark.django_db
def test_spot_update_preserves_original_author_when_author_id_is_posted(client):
    owner = create_user("spot-owner@test.com", "spotowner")
    other_user = create_user("spot-attacker@test.com", "spotattacker")
    spot = create_spot(owner, name="Original")
    client.force_login(owner)

    response = client.post(
        reverse("spots:spot_update", args=[spot.slug]),
        {
            "author": other_user.pk,
            "name": "Updated",
            "country": "PT",
            "difficulty": Spot.Difficulty.INTERMEDIATE,
            "surf_break_type": Spot.SurfBreakType.POINT_BREAK,
            "wave_direction": Spot.WaveDirection.RIGHT,
            "location_details": "",
            "optimal_swell_direction": "NW",
            "optimal_wind_direction": "E",
            "description": "Updated by owner",
            "latitude": "38.000000",
            "longitude": "-9.000000",
        },
        follow=False,
    )

    spot.refresh_from_db()
    assert response.status_code == 302
    assert spot.author == owner
    assert spot.author != other_user


@pytest.mark.django_db
def test_non_author_cannot_delete_another_users_spot(client):
    owner = create_user("delete-owner@test.com", "deleteowner")
    other_user = create_user("delete-attacker@test.com", "deleteattacker")
    spot = create_spot(owner, name="Protected spot")
    client.force_login(other_user)

    response = client.post(reverse("spots:spot_delete", args=[spot.slug]), follow=False)

    assert response.status_code == 403
    assert Spot.objects.filter(pk=spot.pk).exists()


@pytest.mark.django_db
def test_session_create_ignores_posted_organizer_id(client):
    creator = create_user("creator@test.com", "creator")
    other_user = create_user("posted-organizer@test.com", "postedorganizer")
    spot = create_spot(other_user, name="Selected spot")
    client.force_login(creator)

    response = client.post(
        reverse("surf_sessions:session_create"),
        {
            "organizer": other_user.pk,
            "spot": spot.pk,
            "name": "Created safely",
            "date": (timezone.localdate() + timedelta(days=2)).isoformat(),
            "start_time": "09:00",
            "end_time": "",
            "max_participants": "",
            "note": "",
        },
        follow=False,
    )

    session = Session.objects.get(name="Created safely")
    assert response.status_code == 302
    assert session.organizer == creator
    assert session.organizer != other_user


@pytest.mark.django_db
def test_non_organizer_cannot_post_session_update(client):
    organizer = create_user("session-owner@test.com", "sessionowner")
    other_user = create_user("session-attacker@test.com", "sessionattacker")
    session = create_session(organizer, name="Protected session")
    client.force_login(other_user)

    response = client.post(
        reverse("surf_sessions:session_update", args=[session.pk]),
        {
            "spot": session.spot.pk,
            "name": "Hijacked session",
            "date": session.date.isoformat(),
            "start_time": "10:00",
            "end_time": "",
            "max_participants": "",
            "note": "Changed by another user",
        },
        follow=False,
    )

    session.refresh_from_db()
    assert response.status_code == 302
    assert session.name == "Protected session"
    assert session.organizer == organizer


@pytest.mark.django_db
def test_session_join_adds_request_user_not_posted_user_id(client):
    organizer = create_user("join-owner@test.com", "joinowner")
    joining_user = create_user("joiner@test.com", "joiner")
    other_user = create_user("posted-joiner@test.com", "postedjoiner")
    session = create_session(organizer, name="Join target")
    client.force_login(joining_user)

    response = client.post(
        reverse("surf_sessions:session_join", args=[session.pk]),
        {"user": other_user.pk},
        follow=False,
    )

    assert response.status_code == 302
    assert session.participants.filter(pk=joining_user.pk).exists()
    assert not session.participants.filter(pk=other_user.pk).exists()


@pytest.mark.django_db
def test_session_leave_removes_request_user_not_posted_user_id(client):
    organizer = create_user("leave-owner@test.com", "leaveowner")
    leaving_user = create_user("leaver@test.com", "leaver")
    other_participant = create_user("posted-leaver@test.com", "postedleaver")
    session = create_session(organizer, participant=leaving_user, name="Leave target")
    session.participants.add(other_participant)
    client.force_login(leaving_user)

    response = client.post(
        reverse("surf_sessions:session_leave", args=[session.pk]),
        {"user": other_participant.pk},
        follow=False,
    )

    assert response.status_code == 302
    assert not session.participants.filter(pk=leaving_user.pk).exists()
    assert session.participants.filter(pk=other_participant.pk).exists()


@pytest.mark.django_db
def test_outsider_cannot_post_to_direct_conversation(client):
    sender = create_user("sender@test.com", "sender")
    receiver = create_user("receiver@test.com", "receiver")
    outsider = create_user("outsider@test.com", "outsider")
    conversation = Conversation.get_or_create_direct(sender, receiver)
    client.force_login(outsider)

    response = client.post(
        reverse("chat:conversation_detail", args=[conversation.pk]),
        {"body": "I should not be able to post"},
        follow=False,
    )

    assert response.status_code == 403
    assert not Message.objects.filter(conversation=conversation).exists()


@pytest.mark.django_db
def test_conversation_list_is_scoped_to_current_user(client):
    current_user = create_user("current@test.com", "current")
    visible_user = create_user("visible@test.com", "visible")
    hidden_user = create_user("hidden@test.com", "hidden")
    hidden_peer = create_user("hidden-peer@test.com", "hiddenpeer")
    visible_conversation = Conversation.get_or_create_direct(current_user, visible_user)
    hidden_conversation = Conversation.get_or_create_direct(hidden_user, hidden_peer)
    client.force_login(current_user)

    response = client.get(reverse("chat:conversation_list"))

    assert response.status_code == 200
    assert visible_conversation in response.context["conversations"]
    assert hidden_conversation not in response.context["conversations"]


@pytest.mark.django_db
def test_notification_list_scopes_and_marks_only_current_users_notifications(client):
    current_user = create_user("notified@test.com", "notified")
    actor = create_user("actor@test.com", "actor")
    other_user = create_user("other-notified@test.com", "othernotified")
    own_notification = Notification.objects.create(
        recipient=current_user,
        actor=actor,
        kind=Notification.Kind.FOLLOW,
    )
    other_notification = Notification.objects.create(
        recipient=other_user,
        actor=actor,
        kind=Notification.Kind.FOLLOW,
    )
    client.force_login(current_user)

    response = client.get(reverse("notifications:list"))

    own_notification.refresh_from_db()
    other_notification.refresh_from_db()
    assert response.status_code == 200
    assert own_notification in response.context["notifications"]
    assert other_notification not in response.context["notifications"]
    assert own_notification.is_read is True
    assert other_notification.is_read is False
