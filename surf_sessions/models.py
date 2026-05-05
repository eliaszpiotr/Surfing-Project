import logging

from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.validators import MinValueValidator
from django.db import models

from spots.models import Spot

logger = logging.getLogger(__name__)


class Session(models.Model):
    """A surf session at a specific spot, organised by one user, joined by many."""

    name = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        help_text="A descriptive name for the session.",
    )

    spot = models.ForeignKey(
        Spot,
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_sessions",
    )

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="joined_sessions",
        blank=True,
    )

    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    max_participants = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
    )
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["date", "start_time"]),
            models.Index(fields=["organizer", "date"]),
        ]

    def __str__(self):
        """Return a human-readable summary of the session."""
        return f"{self.spot.name} – {self.date} at {self.start_time} (organizer: {self.organizer})"

    @property
    def participants_count(self):
        """Return the current number of participants."""
        return self.participants.count()

    @property
    def is_full(self):
        """Return True if the session has reached its participant limit."""
        if self.max_participants is None:
            return False
        return self.participants_count >= self.max_participants

    def save(self, *args, **kwargs):
        """Save the session and automatically add the organizer as a participant."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.participants.add(self.organizer)

    def can_join(self, user):
        """Return True if the user is allowed to join this session."""
        if not user.is_authenticated:
            return False
        if user == self.organizer:
            return True
        if self.participants.filter(pk=user.pk).exists():
            return False
        if self.max_participants is not None and self.is_full:
            return False
        return True

    def remove_participant(self, user):
        """Remove a participant; raises PermissionDenied if the user is the organizer."""
        if user == self.organizer:
            raise PermissionDenied("Organizer cannot be removed from their own session.")
        self.participants.remove(user)

    def clean(self):
        """Validate that the session name is not blank and end time is after start time."""
        if not self.name or self.name.strip() == "":
            raise ValidationError("Session name cannot be empty.")

        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "End time must be after start time."})
