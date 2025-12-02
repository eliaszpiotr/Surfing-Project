from django.db import models
from django.conf import settings
from spots.models import Spot


class Session(models.Model):
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

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.spot.name} – {self.date} at {self.start_time} (organizer: {self.organizer})"

    @property
    def participants_count(self):
        return self.participants.count()

    @property
    def is_full(self):
        if self.max_participants is None:
            return False
        return self.participants_count >= self.max_participants

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.participants.add(self.organizer)

    def can_join(self, user):
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
        if user == self.organizer:
            raise Exception("Organizer cannot be removed from their own session.")
        self.participants.remove(user)