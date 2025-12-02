from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import  ListView, DetailView, CreateView, UpdateView, DeleteView

from .forms import SessionForm
from .models import Session
from spots.models import Spot


class SessionOrganizerOrStaffRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        session = self.get_object()
        user = self.request.user
        return user.is_staff or user == session.organizer

    def handle_no_permission(self):
        # If not authenticated, let LoginRequiredMixin handle redirect
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()

        # Authenticated but not allowed
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("You are not allowed to modify this session.")


class SessionListView(LoginRequiredMixin, ListView):
    model = Session
    template_name = "surf_sessions/session_list.html"
    context_object_name = "sessions"

    def get_queryset(self):
        # Simple list for now – you can later filter by user/spot/date etc.
        return (
            Session.objects
            .select_related("spot", "organizer")
            .order_by("date", "start_time")
        )


class SessionDetailView(LoginRequiredMixin, DetailView):
    model = Session
    template_name = "surf_sessions/session_detail.html"
    context_object_name = "session"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        user = self.request.user

        context["can_join"] = session.can_join(user)
        context["already_joined"] = (
                user.is_authenticated
                and session.participants.filter(pk=user.pk).exists()
        )
        context["is_organizer"] = user.is_authenticated and user == session.organizer
        context["is_staff"] = user.is_staff

        return context


class SessionCreateView(LoginRequiredMixin, CreateView):
    model = Session
    form_class = SessionForm
    template_name = "surf_sessions/session_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        spot_id = self.request.GET.get("spot")
        if spot_id:
            spot = get_object_or_404(Spot, pk=spot_id)
            kwargs.setdefault("initial", {})
            kwargs["initial"]["spot"] = spot
        return kwargs

    def form_valid(self, form):
        # Do not commit yet, we want to set organizer and spot
        session = form.save(commit=False)

        # Always set organizer to currently logged in user
        session.organizer = self.request.user

        # Ensure spot is set – either from form or from URL (?spot=ID)
        if not session.spot_id:
            spot_id = self.request.GET.get("spot") or self.request.POST.get("spot")
            if spot_id:
                session.spot = get_object_or_404(Spot, pk=spot_id)

        # Now spot *must* be set – if nie, to jest błąd w logice
        if session.spot_id is None:
            messages.error(self.request, "Spot is missing for this session.")
            return self.form_invalid(form)

        session.save()

        # Add organizer as a participant
        session.participants.add(self.request.user)

        messages.success(
            self.request,
            "Session has been created and you have been added as a participant.",
        )

        return redirect(self.get_success_url(session))

    def get_success_url(self, session=None):
        if session is None:
            session = self.object
        # After creating a session, go back to the spot detail
        return reverse("spots:spot_detail", kwargs={"slug": session.spot.slug})


class SessionUpdateView(
    LoginRequiredMixin,
    SessionOrganizerOrStaffRequiredMixin,
    UpdateView,
):
    model = Session
    form_class = SessionForm
    template_name = "surf_sessions/session_form.html"
    context_object_name = "session"

    def form_valid(self, form):
        session = form.save(commit=False)
        # Organizer should not change through the form
        session.organizer = self.get_object().organizer
        session.save()
        messages.success(self.request, "Session has been updated.")
        return redirect(self.get_success_url(session))

    def get_success_url(self, session=None):
        if session is None:
            session = self.object
        return reverse("spots:spot_detail", kwargs={"slug": session.spot.slug})


class SessionDeleteView(
    LoginRequiredMixin,
    SessionOrganizerOrStaffRequiredMixin,
    DeleteView,
):
    model = Session
    template_name = "surf_sessions/session_confirm_delete.html"
    context_object_name = "session"
    success_url = reverse_lazy("spots:spot_list")

    def get_success_url(self):
        # After deleting, go back to the spot where the session belonged
        spot = self.get_object().spot
        messages.success(self.request, "Session has been deleted.")
        return reverse("spots:spot_detail", kwargs={"slug": spot.slug})


class SessionJoinView(LoginRequiredMixin, View):

    def post(self, request, pk):
        session = get_object_or_404(Session, pk=pk)

        if not session.can_join(request.user):
            messages.error(request, "You cannot join this session.")
            return redirect("surf_sessions:session_detail", pk=pk)

        session.participants.add(request.user)
        messages.success(request, "You have joined this session.")
        return redirect("surf_sessions:session_detail", pk=pk)


class SessionLeaveView(LoginRequiredMixin, View):

    def post(self, request, pk):
        session = get_object_or_404(Session, pk=pk)

        if request.user == session.organizer:
            messages.error(request, "Organizer cannot leave their own session.")
            return redirect("surf_sessions:session_detail", pk=pk)

        session.participants.remove(request.user)
        messages.success(request, "You have left this session.")
        return redirect("surf_sessions:session_detail", pk=pk)
