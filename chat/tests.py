from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from chat.models import Conversation, Message
from spots.models import Spot
from surf_sessions.models import Session

User = get_user_model()


def create_user(email, username):
    """Create a reusable user for chat tests."""
    return User.objects.create_user(email=email, username=username, password="pass1234")


def create_session(organizer, participant=None):
    """Create a basic future session with an optional extra participant."""
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
def test_direct_start_creates_conversation_and_redirects(client):
    sender = create_user("sender@test.com", "sender")
    target = create_user("target@test.com", "target")
    client.force_login(sender)

    response = client.post(reverse("chat:direct_start", args=[target.username]), follow=False)

    conversation = Conversation.objects.get(kind=Conversation.Kind.DIRECT)
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("chat:conversation_detail", args=[conversation.pk])
    assert set(conversation.participants.values_list("username", flat=True)) == {"sender", "target"}


@pytest.mark.django_db
def test_direct_start_reuses_existing_conversation(client):
    sender = create_user("sender2@test.com", "sender2")
    target = create_user("target2@test.com", "target2")
    existing = Conversation.get_or_create_direct(sender, target)
    client.force_login(sender)

    response = client.post(reverse("chat:direct_start", args=[target.username]), follow=False)

    assert response.status_code == 302
    assert Conversation.objects.filter(kind=Conversation.Kind.DIRECT).count() == 1
    assert response.headers["Location"] == reverse("chat:conversation_detail", args=[existing.pk])


@pytest.mark.django_db
def test_direct_start_disallows_chat_with_self(client):
    user = create_user("selfchat@test.com", "selfchat")
    client.force_login(user)

    response = client.post(reverse("chat:direct_start", args=[user.username]), follow=False)

    assert response.status_code == 302
    assert not Conversation.objects.exists()


@pytest.mark.django_db
def test_only_participants_can_view_direct_conversation(client):
    sender = create_user("a@test.com", "alpha")
    target = create_user("b@test.com", "beta")
    outsider = create_user("c@test.com", "gamma")
    conversation = Conversation.get_or_create_direct(sender, target)

    client.force_login(outsider)
    response = client.get(reverse("chat:conversation_detail", args=[conversation.pk]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_direct_conversation_post_creates_message(client):
    sender = create_user("poster@test.com", "poster")
    target = create_user("receiver@test.com", "receiver")
    conversation = Conversation.get_or_create_direct(sender, target)
    client.force_login(sender)

    response = client.post(
        reverse("chat:conversation_detail", args=[conversation.pk]),
        {"body": "Hello there"},
        follow=False,
    )

    assert response.status_code == 302
    message = Message.objects.get(conversation=conversation)
    assert message.author == sender
    assert message.body == "Hello there"


@pytest.mark.django_db
@override_settings(
    RATE_LIMITS={
        "message_user": {"limit": 1, "window": 60},
    }
)
def test_direct_message_post_is_rate_limited(client):
    sender = create_user("limitposter@test.com", "limitposter")
    target = create_user("limitreceiver@test.com", "limitreceiver")
    conversation = Conversation.get_or_create_direct(sender, target)
    cache.clear()
    client.force_login(sender)

    assert client.post(reverse("chat:conversation_detail", args=[conversation.pk]), {"body": "First"}).status_code == 302
    response = client.post(reverse("chat:conversation_detail", args=[conversation.pk]), {"body": "Second"})

    assert response.status_code == 429
    assert Message.objects.filter(conversation=conversation).count() == 1
    cache.clear()


@pytest.mark.django_db
def test_session_chat_post_allows_participant(client):
    organizer = create_user("org@test.com", "organizer")
    participant = create_user("part@test.com", "participant")
    session = create_session(organizer, participant=participant)
    client.force_login(participant)

    response = client.post(
        reverse("chat:session_message_create", args=[session.pk]),
        {"body": "See you there"},
        follow=False,
    )

    assert response.status_code == 302
    conversation = Conversation.objects.get(session=session)
    message = Message.objects.get(conversation=conversation)
    assert message.author == participant
    assert message.body == "See you there"


@pytest.mark.django_db
def test_session_chat_post_rejects_outsider(client):
    organizer = create_user("org2@test.com", "organizer2")
    outsider = create_user("outsider@test.com", "outsider")
    session = create_session(organizer)
    client.force_login(outsider)

    response = client.post(
        reverse("chat:session_message_create", args=[session.pk]),
        {"body": "I should not post"},
        follow=False,
    )

    assert response.status_code == 302
    assert not Conversation.objects.filter(session=session).exists()


@pytest.mark.django_db
def test_session_detail_shows_chat_form_for_participant(client):
    organizer = create_user("org3@test.com", "organizer3")
    participant = create_user("part3@test.com", "participant3")
    session = create_session(organizer, participant=participant)
    conversation = Conversation.get_or_create_session_conversation(session)
    Message.objects.create(conversation=conversation, author=organizer, body="Forecast looks good")
    client.force_login(participant)

    response = client.get(reverse("surf_sessions:session_detail", args=[session.pk]))

    assert response.status_code == 200
    assert response.context["can_access_session_chat"] is True
    assert response.context["session_chat"] == conversation
    assert "Forecast looks good" in response.content.decode()
