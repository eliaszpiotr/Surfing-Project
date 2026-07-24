from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from chat.consumers import DirectChatConsumer, SessionChatConsumer
from chat.models import Conversation, Message
from notifications.models import Notification
from spots.models import Spot
from surf_sessions.models import Session

User = get_user_model()

TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


def create_user(email, username):
    return User.objects.create_user(email=email, username=username, password="pass1234")


def create_session(organizer, participant=None):
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


def direct_communicator(conversation, user):
    communicator = WebsocketCommunicator(
        DirectChatConsumer.as_asgi(),
        f"/ws/chat/direct/{conversation.pk}/",
    )
    communicator.scope["user"] = user
    communicator.scope["url_route"] = {"kwargs": {"conversation_id": conversation.pk}}
    return communicator


def session_communicator(session, user):
    communicator = WebsocketCommunicator(
        SessionChatConsumer.as_asgi(),
        f"/ws/chat/session/{session.pk}/",
    )
    communicator.scope["user"] = user
    communicator.scope["url_route"] = {"kwargs": {"session_id": session.pk}}
    return communicator


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
def test_direct_chat_websocket_rejects_non_participant():
    sender = create_user("ws-sender@test.com", "wssender")
    target = create_user("ws-target@test.com", "wstarget")
    outsider = create_user("ws-outsider@test.com", "wsoutsider")
    conversation = Conversation.get_or_create_direct(sender, target)
    communicator = direct_communicator(conversation, outsider)

    connected, _ = async_to_sync(communicator.connect)()

    assert connected is False


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
def test_direct_chat_websocket_creates_message_and_broadcasts_to_participants():
    cache.clear()
    sender = create_user("ws-sender2@test.com", "wssender2")
    target = create_user("ws-target2@test.com", "wstarget2")
    conversation = Conversation.get_or_create_direct(sender, target)
    sender_socket = direct_communicator(conversation, sender)
    target_socket = direct_communicator(conversation, target)

    async def exchange_message():
        try:
            sender_connected, _ = await sender_socket.connect()
            target_connected, _ = await target_socket.connect()

            assert sender_connected is True
            assert target_connected is True

            await sender_socket.send_json_to({"body": "Hello over socket"})
            return await target_socket.receive_json_from()
        finally:
            await sender_socket.disconnect()
            await target_socket.disconnect()

    event = async_to_sync(exchange_message)()
    message = Message.objects.get(conversation=conversation)
    notification = Notification.objects.get(message=message)
    assert event["type"] == "message"
    assert event["message"]["body"] == "Hello over socket"
    assert event["message"]["author_username"] == sender.username
    assert message.author == sender
    assert notification.recipient == target
    cache.clear()


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
def test_session_chat_websocket_allows_participant_and_creates_notification():
    cache.clear()
    organizer = create_user("ws-org@test.com", "wsorganizer")
    participant = create_user("ws-part@test.com", "wsparticipant")
    session = create_session(organizer, participant=participant)
    organizer_socket = session_communicator(session, organizer)
    participant_socket = session_communicator(session, participant)

    async def exchange_message():
        try:
            organizer_connected, _ = await organizer_socket.connect()
            participant_connected, _ = await participant_socket.connect()

            assert organizer_connected is True
            assert participant_connected is True

            await participant_socket.send_json_to({"body": "Forecast looks good"})
            return await organizer_socket.receive_json_from()
        finally:
            await organizer_socket.disconnect()
            await participant_socket.disconnect()

    event = async_to_sync(exchange_message)()
    conversation = Conversation.objects.get(session=session)
    message = Message.objects.get(conversation=conversation)
    notification = Notification.objects.get(message=message)
    assert event["type"] == "message"
    assert event["message"]["body"] == "Forecast looks good"
    assert message.author == participant
    assert notification.recipient == organizer
    cache.clear()


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
def test_session_chat_websocket_rejects_outsider():
    organizer = create_user("ws-org2@test.com", "wsorganizer2")
    outsider = create_user("ws-outsider2@test.com", "wsoutsider2")
    session = create_session(organizer)
    communicator = session_communicator(session, outsider)

    connected, _ = async_to_sync(communicator.connect)()

    assert connected is False
