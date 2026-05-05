from django.contrib import admin

from .models import Spot, SpotPhoto


@admin.register(Spot)
class SpotAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "difficulty", "author", "created_at")
    list_filter = ("difficulty", "country")
    search_fields = ("name", "author__email", "description")
    readonly_fields = ("slug", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(SpotPhoto)
class SpotPhotoAdmin(admin.ModelAdmin):
    list_display = ("spot", "author", "caption", "created_at")
    list_filter = ("created_at",)
    search_fields = ("spot__name", "author__email", "caption")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
