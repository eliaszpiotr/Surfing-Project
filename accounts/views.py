from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView, UpdateView

from .forms import (
    CustomUserCreationForm,
    UserProfileForm,
    CustomAuthenticationForm,
)
from .models import UserProfile
from notifications.services import create_follow_notification
from spots.models import SpotPhoto
from surf_sessions.models import Session
from surfingproject.rate_limits import (
    client_ip_identifier,
    posted_value_identifier,
    rate_limited_response,
    user_or_ip_identifier,
)

User = get_user_model()


def build_profile_context(profile_user, viewer=None):
    """Build the profile context for either the current user or a public profile page."""
    today = now().date()
    return {
        "profile_user": profile_user,
        "profile": getattr(profile_user, "profile", None),
        "followers_count": profile_user.followers.count(),
        "following_count": profile_user.following.count(),
        "is_following_profile_user": (
            viewer.is_authenticated
            and viewer != profile_user
            and viewer.is_following(profile_user)
        ) if viewer else False,
        "upcoming_sessions": (
            Session.objects.filter(participants=profile_user, date__gte=today)
            .select_related("spot", "organizer")
            .prefetch_related("participants")
            .order_by("date", "start_time")
        ),
        "history_sessions": (
            Session.objects.filter(participants=profile_user, date__lt=today)
            .select_related("spot", "organizer")
            .prefetch_related("participants")
            .order_by("-date", "-start_time")
        ),
        "uploaded_spot_photos": (
            SpotPhoto.objects.filter(author=profile_user)
            .select_related("spot")
            .order_by("-created_at")
        ),
    }


class RegisterView(FormView):
    """Register a new user, auto-login, and redirect to profile settings."""

    template_name = "accounts/register.html"
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("accounts:profile_settings")

    def post(self, request, *args, **kwargs):
        limited = rate_limited_response(request, "register_ip", client_ip_identifier(request))
        if limited:
            return limited

        limited = rate_limited_response(request, "register_email", posted_value_identifier(request, "email"))
        if limited:
            return limited

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        """Save the new user, log them in, and proceed to success URL."""
        user = form.save()
        # UserProfile is created automatically by the post_save signal in signals.py.
        login(self.request, user)
        messages.success(self.request, "Your account has been created.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class CustomLoginView(LoginView):
    """Login view using email as the username field."""

    template_name = "accounts/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        limited = rate_limited_response(request, "login_ip", client_ip_identifier(request))
        if limited:
            return limited

        limited = rate_limited_response(request, "login_account", posted_value_identifier(request, "username"))
        if limited:
            return limited

        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        """Redirect to 'next' if safe, otherwise fall back to home."""
        next_url = self.get_redirect_url()
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={self.request.get_host()}):
            return next_url
        return reverse("home")

    def form_invalid(self, form):
        messages.error(self.request, "Incorrect email or password.")
        return super().form_invalid(form)


class LogoutView(View):
    """Log the user out via POST and redirect to home."""

    def post(self, request):
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect("home")


class ProfileView(LoginRequiredMixin, TemplateView):
    """Display the authenticated user's profile with upcoming sessions."""

    template_name = "accounts/profile.html"
    login_url = "accounts:login"

    def get_context_data(self, **kwargs):
        """Add profile, upcoming sessions, and session history to the context."""
        context = super().get_context_data(**kwargs)
        context.update(build_profile_context(self.request.user, viewer=self.request.user))
        context["is_own_profile"] = True
        return context


class ProfileSettingsView(LoginRequiredMixin, UpdateView):
    """Allow the authenticated user to edit their profile."""

    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/profile_settings.html"
    success_url = reverse_lazy("accounts:profile")
    login_url = "accounts:login"

    def get_object(self, queryset=None):
        """Return the profile belonging to the current user."""
        return self.request.user.profile

    def post(self, request, *args, **kwargs):
        if request.FILES:
            limited = rate_limited_response(request, "upload_user", user_or_ip_identifier(request))
            if limited:
                return limited

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class PublicProfileView(TemplateView):
    """Display a public profile page for a user identified by username."""

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context.update(build_profile_context(profile_user, viewer=self.request.user))
        context["is_own_profile"] = self.request.user.is_authenticated and self.request.user == profile_user
        return context


class FollowToggleView(LoginRequiredMixin, View):
    """Toggle follow/unfollow for the target user identified by username."""

    login_url = "accounts:login"

    def post(self, request, username):
        limited = rate_limited_response(request, "follow_user", user_or_ip_identifier(request))
        if limited:
            return limited

        target_user = get_object_or_404(User, username=username)

        if request.user == target_user:
            messages.error(request, "You cannot follow your own profile.")
            return redirect("accounts:user_profile", username=target_user.username)

        if request.user.is_following(target_user):
            request.user.following.remove(target_user)
            messages.success(request, f"You unfollowed @{target_user.username}.")
        else:
            request.user.following.add(target_user)
            create_follow_notification(actor=request.user, recipient=target_user)
            messages.success(request, f"You are now following @{target_user.username}.")

        return redirect("accounts:user_profile", username=target_user.username)
