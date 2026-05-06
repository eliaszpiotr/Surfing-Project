from django.urls import path
from .views import RegisterView, CustomLoginView, ProfileView, ProfileSettingsView, LogoutView, PublicProfileView

app_name = "accounts"
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/settings/", ProfileSettingsView.as_view(), name="profile_settings"),
    path("users/<str:username>/", PublicProfileView.as_view(), name="user_profile"),
]
