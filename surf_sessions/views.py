import logging

from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone

logger = logging.getLogger(__name__)

from .models import Session
from .forms import SessionForm
from spots.models import Spot
from chat.forms import MessageForm
from chat.models import Conversation
from surfingproject.rate_limits import rate_limited_response, user_or_ip_identifier


class SessionListView(LoginRequiredMixin, ListView):
    """Paginated list of upcoming surf sessions, visible to authenticated users only."""

    model = Session
    template_name = "surf_sessions/session_list.html"
    context_object_name = "sessions"

    def get_queryset(self):
        """Return only future sessions, optimised with select/prefetch."""
        today = timezone.localdate()
        return (
            Session.objects
            .filter(date__gte=today)
            .select_related("spot", "organizer")
            .prefetch_related("participants")
            .order_by("date", "start_time")
        )


class SessionDetailView(DetailView):
    """Detail page for a single surf session, including join/leave context flags."""

    model = Session
    template_name = "surf_sessions/session_detail.html"
    context_object_name = "session"

    def get_queryset(self):
        """Return sessions with related spot and participants pre-fetched."""
        return Session.objects.select_related("spot", "organizer").prefetch_related("participants")

    def get_context_data(self, **kwargs):
        """Add organizer, join eligibility, and participation flags to the context."""
        context = super().get_context_data(**kwargs)
        session = self.object
        user = self.request.user

        context["is_organizer"] = user.is_authenticated and user == session.organizer
        context["already_joined"] = session.participants.filter(pk=user.pk).exists()
        context["can_join"] = session.can_join(user)
        context["can_access_session_chat"] = (
            user.is_authenticated
            and (user == session.organizer or session.participants.filter(pk=user.pk).exists())
        )
        context["session_chat"] = (
            Conversation.objects
            .filter(session=session)
            .prefetch_related("messages__author")
            .first()
        )
        context["session_chat_form"] = MessageForm() if context["can_access_session_chat"] else None

        return context


class SessionCreateView(LoginRequiredMixin, CreateView):
    """Create a new surf session, optionally preselecting a spot from the query string."""

    model = Session
    form_class = SessionForm
    template_name = "surf_sessions/session_form.html"

    def dispatch(self, request, *args, **kwargs):
        """Optionally bind the form to a specific spot from ?spot=<id>."""
        if request.method == "POST":
            limited = rate_limited_response(request, "session_write_user", user_or_ip_identifier(request))
            if limited:
                return limited

        spot_id = request.GET.get("spot")
        self.spot = get_object_or_404(Spot, pk=spot_id) if spot_id else None
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass the fixed spot to the form so it can be rendered as a hidden field."""
        kwargs = super().get_form_kwargs()
        kwargs["fixed_spot"] = self.spot
        return kwargs

    def get_context_data(self, **kwargs):
        """Add the target spot to the template context."""
        context = super().get_context_data(**kwargs)
        context["spot"] = self.spot
        return context

    def form_valid(self, form):
        """Assign the current user as organizer and the chosen spot before saving."""
        session = form.save(commit=False)
        session.organizer = self.request.user
        session.spot = self.spot or form.cleaned_data["spot"]
        session.save()
        messages.success(self.request, "Session created successfully!")
        return redirect("spots:spot_detail", slug=session.spot.slug)


class SessionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edit an existing surf session; only the organizer may access this view."""

    model = Session
    form_class = SessionForm
    template_name = "surf_sessions/session_form.html"
    context_object_name = "session"

    def test_func(self):
        """Return True only if the current user is the session organizer."""
        return self.request.user == self.get_object().organizer

    def handle_no_permission(self):
        """Redirect non-organizers to the session detail page with an error message."""
        messages.error(self.request, "Only the organizer can edit this session.")
        return redirect("surf_sessions:session_detail", pk=self.get_object().pk)

    def form_valid(self, form):
        """Save changes and redirect to the session detail page."""
        limited = rate_limited_response(self.request, "session_write_user", user_or_ip_identifier(self.request))
        if limited:
            return limited

        session = form.save()
        messages.success(self.request, "Session updated.")
        return redirect("surf_sessions:session_detail", pk=session.pk)


class SessionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a surf session; only the organizer may perform this action."""

    model = Session
    template_name = "surf_sessions/session_confirm_delete.html"
    context_object_name = "session"

    def test_func(self):
        """Return True only if the current user is the session organizer."""
        return self.request.user == self.get_object().organizer

    def handle_no_permission(self):
        """Redirect non-organizers to the session detail page with an error message."""
        messages.error(self.request, "Only the organizer can delete this session.")
        return redirect("surf_sessions:session_detail", pk=self.get_object().pk)

    def get_success_url(self):
        """Redirect to the parent spot's detail page after deletion."""
        return reverse_lazy("spots:spot_detail", kwargs={"slug": self.object.spot.slug})


class SessionJoinView(LoginRequiredMixin, View):
    """Handle POST requests to join a surf session."""

    def post(self, request, pk):
        """Add the current user to the session's participants if eligible."""
        limited = rate_limited_response(request, "session_write_user", user_or_ip_identifier(request))
        if limited:
            return limited

        session = get_object_or_404(Session, pk=pk)
        if not session.can_join(request.user):
            messages.error(request, "You cannot join this session.")
            return redirect("surf_sessions:session_detail", pk=session.pk)

        session.participants.add(request.user)
        messages.success(request, "You joined the session!")
        return redirect("surf_sessions:session_detail", pk=session.pk)


class SessionLeaveView(LoginRequiredMixin, View):
    """Handle POST requests to leave a surf session."""

    def post(self, request, pk):
        """Remove the current user from the session's participants."""
        limited = rate_limited_response(request, "session_write_user", user_or_ip_identifier(request))
        if limited:
            return limited

        session = get_object_or_404(Session, pk=pk)
        try:
            session.remove_participant(request.user)
            messages.success(request, "You left the session.")
        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception:
            logger.exception("Unexpected error while leaving session %s", pk)
            messages.error(request, "Something went wrong. Please try again.")

        return redirect("surf_sessions:session_detail", pk=session.pk)
