from django.contrib import admin

from .models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """
    Admin configuration for surf surf_sessions.
    """

    list_display = (
        "spot",
        "date",
        "start_time",
        "organizer",
        "participants_count",
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
