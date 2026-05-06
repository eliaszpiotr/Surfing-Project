from django.urls import path

from .views import ConversationListView, DirectConversationDetailView, DirectConversationStartView, SessionMessageCreateView

app_name = "chat"

urlpatterns = [
    path("", ConversationListView.as_view(), name="conversation_list"),
    path("direct/start/<str:username>/", DirectConversationStartView.as_view(), name="direct_start"),
    path("direct/<int:pk>/", DirectConversationDetailView.as_view(), name="conversation_detail"),
    path("session/<int:session_pk>/message/", SessionMessageCreateView.as_view(), name="session_message_create"),
]

