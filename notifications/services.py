import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from django.utils.formats import date_format

from .models import Notification

logger = logging.getLogger(__name__)


def create_follow_notification(actor, recipient):
    """Create a follow notification unless the recipient is the actor."""
    if actor == recipient:
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        kind=Notification.Kind.FOLLOW,
    )
    send_notification_event(notification)
    return notification


def create_direct_message_notification(message):
    """Notify the other participant in a direct conversation."""
    conversation = message.conversation
    recipient = conversation.other_participant(message.author)
    if not recipient or recipient == message.author:
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        actor=message.author,
        kind=Notification.Kind.DIRECT_MESSAGE,
        conversation=conversation,
        message=message,
    )
    send_notification_event(notification)
    return notification


def create_session_message_notifications(message):
    """Notify all other session chat participants."""
    conversation = message.conversation
    session = conversation.session
    if not session:
        return []

    recipients = session.participants.exclude(pk=message.author.pk)
    notifications = []
    for recipient in recipients:
        notifications.append(
            Notification.objects.create(
                recipient=recipient,
                actor=message.author,
                kind=Notification.Kind.SESSION_MESSAGE,
                conversation=conversation,
                session=session,
                message=message,
            )
        )
    for notification in notifications:
        send_notification_event(notification)
    return notifications


def send_notification_event(notification):
    """Push a notification update to the recipient's WebSocket channel."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"notifications_user_{notification.recipient_id}",
            {
                "type": "notification.created",
                "notification": serialize_notification(notification),
                "unread_count": Notification.objects.filter(
                    recipient=notification.recipient,
                    is_read=False,
                ).count(),
            },
        )
    except Exception:
        logger.warning("Failed to send live notification event.", exc_info=True)


def serialize_notification(notification):
    created_at = timezone.localtime(notification.created_at)
    return {
        "id": notification.pk,
        "body": notification.body,
        "target_url": notification.target_url,
        "created_at": date_format(created_at, "M j, Y H:i"),
    }
