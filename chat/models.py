from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from core.validators import ALLOWED_IMAGE_EXTENSIONS, validate_uploaded_image
from surfingproject.uploads import chat_message_image_upload_path


class Conversation(models.Model):
    """Conversation container for either a direct chat or a session chat."""

    class Kind(models.TextChoices):
        DIRECT = "direct", "Direct"
        SESSION = "session", "Session"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="chat_conversations",
        blank=True,
    )
    session = models.OneToOneField(
        "surf_sessions.Session",
        on_delete=models.CASCADE,
        related_name="chat_conversation",
        null=True,
        blank=True,
    )
    direct_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        """Return a readable conversation label."""
        if self.kind == self.Kind.SESSION and self.session_id:
            return f"Session chat: {self.session.name}"
        return f"Direct chat {self.direct_key or self.pk}"

    @classmethod
    def build_direct_key(cls, user_a, user_b):
        """Build a deterministic key for a pair of users."""
        if user_a.pk == user_b.pk:
            raise ValueError("Cannot create a direct conversation with the same user.")
        low_id, high_id = sorted([user_a.pk, user_b.pk])
        return f"{low_id}:{high_id}"

    @classmethod
    def get_or_create_direct(cls, user_a, user_b):
        """Return the unique direct conversation for two users."""
        key = cls.build_direct_key(user_a, user_b)
        conversation, created = cls.objects.get_or_create(
            direct_key=key,
            defaults={"kind": cls.Kind.DIRECT},
        )
        if created or conversation.participants.count() < 2:
            conversation.participants.add(user_a, user_b)
        return conversation

    @classmethod
    def get_or_create_session_conversation(cls, session):
        """Return the singleton conversation for a surf session."""
        conversation, _ = cls.objects.get_or_create(
            session=session,
            defaults={"kind": cls.Kind.SESSION},
        )
        return conversation

    def can_view(self, user):
        """Return True only when the user is allowed to access this conversation."""
        if not getattr(user, "is_authenticated", False):
            return False
        if self.kind == self.Kind.DIRECT:
            return self.participants.filter(pk=user.pk).exists()
        if self.kind == self.Kind.SESSION and self.session_id:
            return user == self.session.organizer or self.session.participants.filter(pk=user.pk).exists()
        return False

    def title_for(self, user):
        """Return a display title tailored to the current viewer."""
        if self.kind == self.Kind.SESSION and self.session_id:
            return self.session.name
        other = self.other_participant(user)
        return f"@{other.username}" if other else "Direct conversation"

    def other_participant(self, user):
        """Return the other participant in a direct conversation."""
        if self.kind != self.Kind.DIRECT:
            return None
        return self.participants.exclude(pk=user.pk).first()


class Message(models.Model):
    """Single message inside a conversation."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    body = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=chat_message_image_upload_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS),
            validate_uploaded_image,
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        """Return a short preview of the message."""
        return f"{self.author}: {self.body[:40]}"

    def save(self, *args, **kwargs):
        """Persist the message and bump the parent conversation timestamp."""
        super().save(*args, **kwargs)
        Conversation.objects.filter(pk=self.conversation_id).update(updated_at=timezone.now())
