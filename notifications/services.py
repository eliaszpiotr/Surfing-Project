from .models import Notification


def create_follow_notification(actor, recipient):
    """Create a follow notification unless the recipient is the actor."""
    if actor == recipient:
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        kind=Notification.Kind.FOLLOW,
    )


def create_direct_message_notification(message):
    """Notify the other participant in a direct conversation."""
    conversation = message.conversation
    recipient = conversation.other_participant(message.author)
    if not recipient or recipient == message.author:
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=message.author,
        kind=Notification.Kind.DIRECT_MESSAGE,
        conversation=conversation,
        message=message,
    )


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
    return notifications

