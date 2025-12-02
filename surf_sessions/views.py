from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone

from .models import Session
from .forms import SessionForm
from spots.models import Spot


class SessionListView(LoginRequiredMixin, ListView):
    model = Session
    template_name = "surf_sessions/session_list.html"
    context_object_name = "sessions"

    def get_queryset(self):
        today = timezone.localdate()
        return Session.objects.filter(date__gte=today).order_by("date", "start_time")


class SessionDetailView(DetailView):
    model = Session
    template_name = "surf_sessions/session_detail.html"
    context_object_name = "session"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        user = self.request.user

        context["is_organizer"] = user.is_authenticated and user == session.organizer
        context["already_joined"] = session.participants.filter(pk=user.pk).exists()
        context["can_join"] = session.can_join(user)

        return context


class SessionCreateView(LoginRequiredMixin, CreateView):
    model = Session
    form_class = SessionForm
    template_name = "surf_sessions/session_form.html"

    def form_valid(self, form):
        session = form.save(commit=False)
        session.organizer = self.request.user

        spot_id = self.request.GET.get("spot")
        session.spot = get_object_or_404(Spot, pk=spot_id)

        session.save()
        messages.success(self.request, "Session created successfully!")
        return redirect("spots:spot_detail", slug=session.spot.slug)


class SessionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Session
    form_class = SessionForm
    template_name = "surf_sessions/session_form.html"
    context_object_name = "session"

    def test_func(self):
        return self.request.user == self.get_object().organizer

    def handle_no_permission(self):
        messages.error(self.request, "Only the organizer can edit this session.")
        return redirect("surf_sessions:session_detail", pk=self.get_object().pk)

    def form_valid(self, form):
        session = form.save()
        messages.success(self.request, "Session updated.")
        return redirect("surf_sessions:session_detail", pk=session.pk)


class SessionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Session
    template_name = "surf_sessions/session_confirm_delete.html"
    context_object_name = "session"

    def test_func(self):
        return self.request.user == self.get_object().organizer

    def handle_no_permission(self):
        messages.error(self.request, "Only the organizer can delete this session.")
        return redirect("surf_sessions:session_detail", pk=self.get_object().pk)

    def get_success_url(self):
        return reverse_lazy("spots:spot_detail", kwargs={"slug": self.object.spot.slug})


class SessionJoinView(LoginRequiredMixin, View):
    def post(self, request, pk):
        session = get_object_or_404(Session, pk=pk)
        if not session.can_join(request.user):
            messages.error(request, "You cannot join this session.")
            return redirect("surf_sessions:session_detail", pk=session.pk)

        session.participants.add(request.user)
        messages.success(request, "You joined the session!")
        return redirect("surf_sessions:session_detail", pk=session.pk)


class SessionLeaveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        session = get_object_or_404(Session, pk=pk)
        try:
            session.remove_participant(request.user)
            messages.success(request, "You left the session.")
        except Exception as e:
            messages.error(request, str(e))

        return redirect("surf_sessions:session_detail", pk=session.pk)