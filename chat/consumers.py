from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils.formats import date_format
from django.utils import timezone

from chat.forms import MessageForm
from chat.models import Conversation, Message
from notifications.services import create_direct_message_notification, create_session_message_notifications
from surf_sessions.models import Session
from surfingproject.rate_limits import TOO_MANY_REQUESTS_MESSAGE, get_rate_limit, is_rate_limited


class BaseChatConsumer(AsyncJsonWebsocketConsumer):
    conversation = None
    group_name = None

    async def connect(self):
        user = self.scope.get("user")
        if not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        self.conversation = await self.get_conversation()
        if not self.conversation:
            await self.close(code=4403)
            return

        self.group_name = f"chat_{self.conversation.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        body = str(content.get("body", ""))
        message_data = await self.create_message(body)

        if message_data.get("error"):
            await self.send_json(message_data)
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "message": message_data,
            },
        )

    async def chat_message(self, event):
        await self.send_json(
            {
                "type": "message",
                "message": event["message"],
            }
        )

    @database_sync_to_async
    def create_message(self, body):
        user = self.scope["user"]
        limit, window = get_rate_limit("message_user")
        if is_rate_limited("message_user", f"user:{user.pk}", limit, window):
            return {
                "type": "error",
                "error": TOO_MANY_REQUESTS_MESSAGE,
            }

        form = MessageForm(data={"body": body})
        if not form.is_valid():
            return {
                "type": "error",
                "error": "Message cannot be empty.",
            }

        message = Message.objects.create(
            conversation=self.conversation,
            author=user,
            body=form.cleaned_data["body"],
        )
        self.create_notifications(message)
        return serialize_message(message)

    def create_notifications(self, message):
        raise NotImplementedError

    async def get_conversation(self):
        raise NotImplementedError


class DirectChatConsumer(BaseChatConsumer):
    @database_sync_to_async
    def get_conversation(self):
        conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        try:
            conversation = Conversation.objects.get(pk=conversation_id, kind=Conversation.Kind.DIRECT)
        except Conversation.DoesNotExist:
            return None

        if not conversation.can_view(self.scope["user"]):
            return None
        return conversation

    def create_notifications(self, message):
        create_direct_message_notification(message)


class SessionChatConsumer(BaseChatConsumer):
    @database_sync_to_async
    def get_conversation(self):
        session_id = self.scope["url_route"]["kwargs"]["session_id"]
        try:
            session = Session.objects.get(pk=session_id)
        except Session.DoesNotExist:
            return None

        can_access = session.organizer_id == self.scope["user"].pk or session.participants.filter(pk=self.scope["user"].pk).exists()
        if not can_access:
            return None

        return Conversation.get_or_create_session_conversation(session)

    def create_notifications(self, message):
        create_session_message_notifications(message)


def serialize_message(message):
    created_at = timezone.localtime(message.created_at)
    return {
        "id": message.pk,
        "author_id": message.author_id,
        "author_username": message.author.username,
        "body": message.body,
        "created_at": date_format(created_at, "M j, Y H:i"),
    }
