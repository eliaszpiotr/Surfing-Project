from django.shortcuts import render
from django.utils.timezone import localdate
from surf_sessions.models import Session

def home(request):
    today = localdate()
    upcoming_sessions = (
        Session.objects.filter(date__gte=today)
        .select_related("spot", "organizer")
        .order_by("date", "start_time")[:10]
    )
    return render(request, "core/home.html", {
        "upcoming_sessions": upcoming_sessions,
    })