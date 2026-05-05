from django.contrib import admin
from django.db.models import Count

from .models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "spot",
        "name",
        "date",
        "start_time",
        "organizer",
        "participant_count",
        "max_participants",
        "created_at",
    )
    list_filter = (
        "date",
        "spot__country",
    )
    search_fields = (
        "spot__name",
        "organizer__username",
        "organizer__email",
    )
    ordering = ("date", "start_time")

    def get_queryset(self, request):
        # Annotate to avoid N+1 queries for participant count
        return super().get_queryset(request).annotate(_participant_count=Count("participants"))

    @admin.display(description="Participants", ordering="_participant_count")
    def participant_count(self, obj):
        return obj._participant_count
