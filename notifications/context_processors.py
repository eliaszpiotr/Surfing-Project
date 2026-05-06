def notification_counts(request):
    """Expose the unread notification count in all templates."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"unread_notifications_count": 0}

    return {
        "unread_notifications_count": request.user.notifications.filter(is_read=False).count()
    }

