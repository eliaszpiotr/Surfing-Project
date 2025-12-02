from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils.timezone import now
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView, UpdateView

from .forms import CustomUserCreationForm, UserProfileForm
from .models import UserProfile
from surf_sessions.models import Session


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("profile_settings")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Your account has been created.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse("home")

    def form_invalid(self, form):
        messages.error(self.request, "Incorrect email or password.")
        return super().form_invalid(form)


class LogoutView(View):

    def post(self, request):
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect("home")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = now().date()

        # User profile object
        profile = getattr(user, "profile", None)

        # Sessions where the user is organizer (upcoming)
        organized_sessions = (
            Session.objects.filter(organizer=user, date__gte=today)
            .select_related("spot")
            .prefetch_related("participants")
            .order_by("date", "start_time")
        )

        # Sessions where the user is a participant but not organizer (upcoming)
        joined_sessions = (
            Session.objects.filter(participants=user, date__gte=today)
            .exclude(organizer=user)
            .select_related("spot", "organizer")
            .prefetch_related("participants")
            .order_by("date", "start_time")
        )

        context["profile"] = profile
        context["organized_sessions"] = organized_sessions
        context["joined_sessions"] = joined_sessions
        return context


class ProfileSettingsView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/profile_settings.html"
    success_url = reverse_lazy("profile")
    login_url = "login"

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)