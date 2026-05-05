from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CustomUser, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name")
    list_filter = ("is_staff", "is_active")
    ordering = ("-date_joined",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "country")
    search_fields = ("user__email", "user__username")
    list_filter = ("country",)
