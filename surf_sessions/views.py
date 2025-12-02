from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    View,
)
from django.http import JsonResponse

from .forms import SessionForm
from .models import Session
from spots.models import Spot


class SessionOrganizerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        session = self.get_object()
        user = self.request.user
        return user.is_authenticated and user == session.organizer

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            # For anonymous users keep default behaviour (redirect to login)
            return super().handle_no_permission()

        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Only the organizer can modify this session.")


class SessionListView(ListView):
    model = Session
    template_name = "surf_sessions/session_list.html"
    context_object_name = "sessions"

    def get_queryset(self):
        today = timezone.localdate()
        # Show only upcoming sessions by default
        return (
            Session.objects
            .filter(date__gte=today)
            .select_related("spot", "organizer")
            .prefetch_related("participants")
            .order_by("date", "start_time")
        )


class SessionDetailView(DetailView):
    model = Session
    template_name = "surf_sessions/session_detail.html"
    context_object_name = "session"


class SessionCreateView(LoginRequiredMixin, CreateView):
    model = Session
    form_class = SessionForm
    template_name = "surf_sessions/session_form.html"
    login_url = "login"
    redirect_field_name = "next"

    def get_initial(self):
        """
        If ?spot=<id> is in the URL, preselect this spot in the form.
        """
        initial = super().get_initial()
        spot_id = self.request.GET.get("spot")
        if spot_id:
            try:
                initial["spot"] = Spot.objects.get(pk=spot_id)
            except Spot.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        session = form.save(commit=False)
        session.organizer = self.request.user

        # If ?spot=<id> is in the URL, force this spot for the session
        spot_id = self.request.GET.get("spot")
        if spot_id:
            session.spot = get_object_or_404(Spot, pk=spot_id)

        session.save()
        # Organizer is automatically added as a participant
        session.participants.add(self.request.user)
        form.save_m2m()  # in case we later add participants field to the form

        messages.success(
            self.request,
            f"Session for '{session.spot.name}' on {session.date} has been created.",
        )
        self.object = session
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("surf_sessions:session_detail", kwargs={"pk": self.object.pk})


class SessionUpdateView(LoginRequiredMixin, SessionOrganizerRequiredMixin, UpdateView):
    model = Session
    form_class = SessionForm
    template_name = "surf_sessions/session_form.html"
    context_object_name = "session"
    login_url = "login"
    redirect_field_name = "next"

    def form_valid(self, form):
        session = form.save()
        messages.success(
            self.request,
            f"Session for '{session.spot.name}' on {session.date} has been updated.",
        )
        self.object = session
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("surf_sessions:session_detail", kwargs={"pk": self.object.pk})


class SessionDeleteView(LoginRequiredMixin, SessionOrganizerRequiredMixin, DeleteView):
    model = Session
    template_name = "surf_sessions/session_confirm_delete.html"
    context_object_name = "session"
    success_url = reverse_lazy("surf_sessions:session_list")
    login_url = "login"
    redirect_field_name = "next"

    def delete(self, request, *args, **kwargs):
        session = self.get_object()
        messages.success(request, f"Session for '{session.spot.name}' on {session.date} has been deleted.")
        return super().delete(request, *args, **kwargs)


class SessionJoinView(LoginRequiredMixin, View):
    login_url = "login"
    redirect_field_name = "next"

    def post(self, request, pk):
        session = get_object_or_404(Session, pk=pk)

        if not session.can_join(request.user):
            messages.error(request, "You cannot join this session.")
        else:
            session.participants.add(request.user)
            messages.success(request, "You have joined this session.")

        next_url = (
                request.POST.get("next")
                or request.META.get("HTTP_REFERER")
                or reverse("surf_sessions:session_detail", args=[session.pk])
        )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "participants": session.participants_count})

        return redirect(next_url)


class SessionLeaveView(LoginRequiredMixin, View):
    login_url = "login"
    redirect_field_name = "next"

    def post(self, request, pk):
        session = get_object_or_404(Session, pk=pk)

        if request.user == session.organizer:
            messages.error(request, "Organizer cannot leave their own session.")
        else:
            session.participants.remove(request.user)
            messages.success(request, "You have left this session.")

        next_url = (
                request.POST.get("next")
                or request.META.get("HTTP_REFERER")
                or reverse("surf_sessions:session_detail", args=[session.pk])
        )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "participants": session.participants_count})

        return redirect(next_url)
