from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """Inbox-style list of notifications for the current user."""

    template_name = "notifications/list.html"
    context_object_name = "notifications"
    login_url = "accounts:login"

    def get_queryset(self):
        """Return notifications scoped to the current user."""
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "actor", "conversation", "session", "message"
        )

    def get(self, request, *args, **kwargs):
        """Mark current notifications as read after listing them."""
        response = super().get(request, *args, **kwargs)
        self.object_list.filter(is_read=False).update(is_read=True)
        return response

