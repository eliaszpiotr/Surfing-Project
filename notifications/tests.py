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
    """Create a reusable user fixture for notifications tests."""
    return User.objects.create_user(email=email, username=username, password="pass1234")


def create_session(organizer, participant=None):
    """Create a future session with an optional second participant."""
    spot = Spot.objects.create(
        name=f"Spot for {organizer.username}",
        author=organizer,
        country="PT",
        latitude=39.355,
        longitude=-9.381,
    )
    session = Session.objects.create(
        name="Morning surf",
        spot=spot,
        organizer=organizer,
        date=timezone.localdate() + timedelta(days=2),
        start_time="08:00",
    )
    if participant:
        session.participants.add(participant)
    return session


@pytest.mark.django_db
def test_follow_creates_notification(client):
    follower = create_user("follower@n.com", "followern")
    target = create_user("target@n.com", "targetn")
    client.force_login(follower)

    response = client.post(reverse("accounts:follow_toggle", args=[target.username]), follow=False)

    assert response.status_code == 302
    notification = Notification.objects.get(recipient=target)
    assert notification.actor == follower
    assert notification.kind == Notification.Kind.FOLLOW


@pytest.mark.django_db
def test_direct_message_creates_notification_for_other_participant(client):
    sender = create_user("sender@n.com", "sendern")
    receiver = create_user("receiver@n.com", "receivern")
    conversation = Conversation.get_or_create_direct(sender, receiver)
    client.force_login(sender)

    response = client.post(reverse("chat:conversation_detail", args=[conversation.pk]), {"body": "Ping"}, follow=False)

    assert response.status_code == 302
    notification = Notification.objects.get(recipient=receiver)
    assert notification.actor == sender
    assert notification.kind == Notification.Kind.DIRECT_MESSAGE


@pytest.mark.django_db
def test_session_message_creates_notification_for_other_participants(client):
    organizer = create_user("organizer@n.com", "orgn")
    participant = create_user("participant@n.com", "partn")
    session = create_session(organizer, participant=participant)
    client.force_login(organizer)

    response = client.post(reverse("chat:session_message_create", args=[session.pk]), {"body": "Wave check"}, follow=False)

    assert response.status_code == 302
    notification = Notification.objects.get(recipient=participant)
    assert notification.actor == organizer
    assert notification.kind == Notification.Kind.SESSION_MESSAGE
    assert notification.session == session


@pytest.mark.django_db
def test_notifications_list_marks_items_as_read(client):
    actor = create_user("actor@n.com", "actorn")
    recipient = create_user("recipient@n.com", "recipientn")
    Notification.objects.create(recipient=recipient, actor=actor, kind=Notification.Kind.FOLLOW)
    client.force_login(recipient)

    response = client.get(reverse("notifications:list"))

    assert response.status_code == 200
    assert Notification.objects.filter(recipient=recipient, is_read=False).count() == 0


@pytest.mark.django_db
def test_notifications_context_count_is_visible_in_nav(client):
    actor = create_user("actor2@n.com", "actor2n")
    recipient = create_user("recipient2@n.com", "recipient2n")
    Notification.objects.create(recipient=recipient, actor=actor, kind=Notification.Kind.FOLLOW)
    client.force_login(recipient)

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert response.context["unread_notifications_count"] == 1
