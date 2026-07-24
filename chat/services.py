import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from django.utils.formats import date_format

logger = logging.getLogger(__name__)


def chat_group_name(conversation_id):
    return f"chat_{conversation_id}"


def broadcast_chat_message(message):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            chat_group_name(message.conversation_id),
            {
                "type": "chat.message",
                "message": serialize_message(message),
            },
        )
    except Exception:
        logger.warning("Failed to broadcast live chat message.", exc_info=True)


def serialize_message(message):
    created_at = timezone.localtime(message.created_at)
    return {
        "id": message.pk,
        "author_id": message.author_id,
        "author_username": message.author.username,
        "body": message.body,
        "image_url": message.image.url if message.image else "",
        "created_at": date_format(created_at, "M j, Y H:i"),
    }
