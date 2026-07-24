from django.urls import path

from .consumers import DirectChatConsumer, SessionChatConsumer

websocket_urlpatterns = [
    path("ws/chat/direct/<int:conversation_id>/", DirectChatConsumer.as_asgi()),
    path("ws/chat/session/<int:session_id>/", SessionChatConsumer.as_asgi()),
]
