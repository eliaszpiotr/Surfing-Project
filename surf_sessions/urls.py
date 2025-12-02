from django.urls import path

from .views import SessionListView, SessionDetailView, SessionCreateView, SessionUpdateView, SessionDeleteView, \
    SessionJoinView, SessionLeaveView

app_name = "surf_sessions"

urlpatterns = [
    path("", SessionListView.as_view(), name="session_list"),
    path("<int:pk>/", SessionDetailView.as_view(), name="session_detail"),
    path("create/", SessionCreateView.as_view(), name="session_create"),
    path("<int:pk>/edit/", SessionUpdateView.as_view(), name="session_update"),
    path("<int:pk>/delete/", SessionDeleteView.as_view(), name="session_delete"),
    path("<int:pk>/join/", SessionJoinView.as_view(), name="session_join"),
    path("<int:pk>/leave/", SessionLeaveView.as_view(), name="session_leave"),
]
