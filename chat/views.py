from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView

from surf_sessions.models import Session
from surfingproject.rate_limits import rate_limited_response, user_or_ip_identifier

from .forms import MessageForm
from .models import Conversation, Message
from .services import broadcast_chat_message, serialize_message
from notifications.services import create_direct_message_notification, create_session_message_notifications

User = get_user_model()


class ConversationAccessMixin(LoginRequiredMixin):
    """Shared access control for direct conversation pages."""

    login_url = "accounts:login"

    def get_object(self, queryset=None):
        conversation = get_object_or_404(
            Conversation.objects.filter(kind=Conversation.Kind.DIRECT).prefetch_related("participants", "messages__author"),
            pk=self.kwargs["pk"],
        )
        if not conversation.can_view(self.request.user):
            raise PermissionDenied("You do not have access to this conversation.")
        return conversation


class ConversationListView(LoginRequiredMixin, ListView):
    """List direct conversations for the current user."""

    template_name = "chat/conversation_list.html"
    context_object_name = "conversations"
    login_url = "accounts:login"

    def get_queryset(self):
        """Return direct conversations ordered by most recent activity."""
        return (
            Conversation.objects.filter(
                kind=Conversation.Kind.DIRECT,
                participants=self.request.user,
            )
            .prefetch_related("participants", "messages__author")
            .order_by("-updated_at", "-created_at")
            .distinct()
        )

    def get_context_data(self, **kwargs):
        """Add precomputed conversation rows for template rendering."""
        context = super().get_context_data(**kwargs)
        conversation_rows = []
        for conversation in context["conversations"]:
            messages_qs = list(conversation.messages.all())
            conversation_rows.append(
                {
                    "conversation": conversation,
                    "other_user": conversation.other_participant(self.request.user),
                    "last_message": messages_qs[-1] if messages_qs else None,
                }
            )
        context["conversation_rows"] = conversation_rows
        return context


class DirectConversationStartView(LoginRequiredMixin, View):
    """Create or reuse a direct conversation and redirect into it."""

    login_url = "accounts:login"

    def post(self, request, username):
        limited = rate_limited_response(request, "conversation_start_user", user_or_ip_identifier(request))
        if limited:
            return limited

        target_user = get_object_or_404(User, username=username)
        if request.user == target_user:
            messages.error(request, "You cannot start a direct chat with yourself.")
            return redirect("accounts:user_profile", username=target_user.username)

        conversation = Conversation.get_or_create_direct(request.user, target_user)
        return redirect("chat:conversation_detail", pk=conversation.pk)


class DirectConversationDetailView(ConversationAccessMixin, DetailView):
    """Show one direct conversation and handle sending new messages."""

    template_name = "chat/conversation_detail.html"
    context_object_name = "conversation"

    def get_context_data(self, **kwargs):
        """Add the message form and target user to the template context."""
        context = super().get_context_data(**kwargs)
        context["message_form"] = kwargs.get("message_form") or MessageForm()
        context["other_user"] = self.object.other_participant(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        """Persist a new direct message from the current user."""
        limited = rate_limited_response(request, "message_user", user_or_ip_identifier(request))
        if limited:
            return limited

        self.object = self.get_object()
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = Message.objects.create(
                conversation=self.object,
                author=request.user,
                body=form.cleaned_data["body"],
                image=form.cleaned_data.get("image"),
            )
            create_direct_message_notification(message)
            broadcast_chat_message(message)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"type": "message", "message": serialize_message(message)})
            return redirect("chat:conversation_detail", pk=self.object.pk)

        context = self.get_context_data(message_form=form)
        return self.render_to_response(context)


class SessionMessageCreateView(LoginRequiredMixin, View):
    """Post a message into a session chat from the session detail page."""

    login_url = "accounts:login"

    def post(self, request, session_pk):
        limited = rate_limited_response(request, "message_user", user_or_ip_identifier(request))
        if limited:
            return limited

        session = get_object_or_404(Session.objects.select_related("organizer"), pk=session_pk)
        can_access = request.user == session.organizer or session.participants.filter(pk=request.user.pk).exists()
        if not can_access:
            messages.error(request, "Only session participants can use this chat.")
            return redirect("surf_sessions:session_detail", pk=session.pk)

        conversation = Conversation.get_or_create_session_conversation(session)
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = Message.objects.create(
                conversation=conversation,
                author=request.user,
                body=form.cleaned_data["body"],
                image=form.cleaned_data.get("image"),
            )
            create_session_message_notifications(message)
            broadcast_chat_message(message)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"type": "message", "message": serialize_message(message)})
        else:
            messages.error(request, "Message cannot be empty.")

        return redirect(f"{reverse('surf_sessions:session_detail', kwargs={'pk': session.pk})}#session-chat")
