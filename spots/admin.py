from django.contrib import admin

from .models import Spot


@admin.register(Spot)
class SpotAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "difficulty", "author", "created_at")
    list_filter = ("difficulty", "country")
    search_fields = ("name", "author__email", "description")
    readonly_fields = ("slug", "created_at", "updated_at")
    ordering = ("-created_at",)