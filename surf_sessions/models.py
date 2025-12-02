from django.db import models
from django.conf import settings
from spots.models import Spot


class Session(models.Model):
    spot = models.ForeignKey(
        Spot,
        on_delete=models.CASCADE,
        related_name="sessions",
        help_text="Surf spot where this session will take place.",
    )

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_sessions",
        help_text="User who created this session.",
    )

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="joined_sessions",
        blank=True,
        help_text="Users who joined this session.",
    )

    date = models.DateField(help_text="Date of the session.")
    start_time = models.TimeField(help_text="Start time of the session.")
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Optional end time of the session.",
    )
    max_participants = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of participants (optional).",
    )
    note = models.TextField(
        blank=True,
        help_text="Additional information (meeting point, required level, etc.).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = "Session"
        verbose_name_plural = "Sessions"

    def __str__(self) -> str:
        return f"{self.spot.name} – {self.date} at {self.start_time} (organizer: {self.organizer})"

    @property
    def participants_count(self) -> int:
        """Return how many users are in the participants list."""
        return self.participants.count()

    @property
    def is_full(self) -> bool:
        if self.max_participants is None:
            return False
        return self.participants_count >= self.max_participants

    def can_join(self, user) -> bool:
        """Return True if given user can join this session."""
        if not user.is_authenticated:
            return False

        # Organizer is already "in" this session; we do not let them join/leave
        if user == self.organizer:
            return False

        # Already joined
        if self.participants.filter(pk=user.pk).exists():
            return False

        # Session is full
        if self.is_full:
            return False

        return True