from django.urls import path
from .views import RegisterView, CustomLoginView, ProfileView, ProfileSettingsView, LogoutView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/settings/", ProfileSettingsView.as_view(), name="profile_settings"),
]