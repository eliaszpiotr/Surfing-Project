import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings

from notifications.consumers import NotificationConsumer
from notifications.services import create_follow_notification

User = get_user_model()

TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


def create_user(email, username):
    return User.objects.create_user(email=email, username=username, password="pass1234")


def notification_communicator(user):
    communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
    communicator.scope["user"] = user
    return communicator


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
def test_notification_websocket_rejects_anonymous_user():
    communicator = notification_communicator(AnonymousUser())

    connected, _ = async_to_sync(communicator.connect)()

    assert connected is False


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
def test_notification_websocket_receives_new_notification_event():
    actor = create_user("notify-actor@test.com", "notifyactor")
    recipient = create_user("notify-recipient@test.com", "notifyrecipient")
    communicator = notification_communicator(recipient)

    async def receive_notification():
        try:
            connected, _ = await communicator.connect()
            assert connected is True

            await database_sync_to_async(create_follow_notification)(actor, recipient)
            return await communicator.receive_json_from()
        finally:
            await communicator.disconnect()

    event = async_to_sync(receive_notification)()

    assert event["type"] == "notification"
    assert event["unread_count"] == 1
    assert event["notification"]["body"] == "@notifyactor started following you."
    assert event["notification"]["target_url"] == "/accounts/users/notifyactor/"
