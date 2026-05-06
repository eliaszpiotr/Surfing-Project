from django.conf import settings
from django.db import models
from django.urls import reverse


class Notification(models.Model):
    """Single user-facing notification entry."""

    class Kind(models.TextChoices):
        FOLLOW = "follow", "Follow"
        DIRECT_MESSAGE = "direct_message", "Direct message"
        SESSION_MESSAGE = "session_message", "Session message"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    conversation = models.ForeignKey(
        "chat.Conversation",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        "surf_sessions.Session",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.ForeignKey(
        "chat.Message",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        """Return a short label for admin/debugging."""
        return f"{self.kind} for {self.recipient}"

    @property
    def target_url(self):
        """Return the most useful destination for the notification."""
        if self.kind == self.Kind.FOLLOW:
            return reverse("accounts:user_profile", args=[self.actor.username])
        if self.kind == self.Kind.DIRECT_MESSAGE and self.conversation_id:
            return reverse("chat:conversation_detail", args=[self.conversation_id])
        if self.kind == self.Kind.SESSION_MESSAGE and self.session_id:
            return f"{reverse('surf_sessions:session_detail', args=[self.session_id])}#session-chat"
        return reverse("notifications:list")

    @property
    def body(self):
        """Return a human-readable notification message."""
        if self.kind == self.Kind.FOLLOW:
            return f"@{self.actor.username} started following you."
        if self.kind == self.Kind.DIRECT_MESSAGE:
            return f"New direct message from @{self.actor.username}."
        if self.kind == self.Kind.SESSION_MESSAGE and self.session:
            return f"New message from @{self.actor.username} in {self.session.name}."
        return "New notification."

