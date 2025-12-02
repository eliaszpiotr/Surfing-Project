from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.text import slugify
import uuid
from django.views import View
from django.http import JsonResponse

from .models import Spot
from .forms import SpotForm


class SpotListView(ListView):
    model = Spot
    template_name = "spots/spot_list.html"
    context_object_name = "spots"


class SpotDetailView(DetailView):
    model = Spot
    template_name = "spots/spot_detail.html"
    context_object_name = "spot"
    slug_field = "slug"
    slug_url_kwarg = "slug"


class SpotCreateView(LoginRequiredMixin, CreateView):
    model = Spot
    form_class = SpotForm
    template_name = "spots/spot_form.html"

    login_url = "login"
    redirect_field_name = "next"

    def form_valid(self, form):
        spot = form.save(commit=False)
        spot.author = self.request.user

        if not spot.slug:
            spot.slug = slugify(spot.name) + "-" + str(uuid.uuid4())[:8]

        spot.save()
        messages.success(
            self.request,
            f"Surf spot '{spot.name}' has been added successfully!",
        )
        self.object = spot
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("spots:spot_detail", kwargs={"slug": self.object.slug})


class AuthorOrStaffMixin(UserPassesTestMixin):

    def test_func(self):
        spot = self.get_object()
        user = self.request.user
        return user.is_authenticated and (user.is_staff or spot.author == user)


class SpotUpdateView(LoginRequiredMixin, AuthorOrStaffMixin, UpdateView):
    model = Spot
    form_class = SpotForm
    template_name = "spots/spot_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    login_url = "login"

    def form_valid(self, form):
        messages.success(self.request, f"Spot '{self.object.name}' has been updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("spots:spot_detail", kwargs={"slug": self.object.slug})


class SpotDeleteView(LoginRequiredMixin, AuthorOrStaffMixin, DeleteView):
    model = Spot
    template_name = "spots/spot_confirm_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    login_url = "login"

    def delete(self, request, *args, **kwargs):
        spot = self.get_object()
        messages.success(request, f"Spot '{spot.name}' has been deleted.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("spots:spot_list")


class SpotMapDataView(View):
    def get(self, request):
        spots = (
            Spot.objects
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
        )

        data = [
            {
                "name": spot.name,
                "slug": spot.slug,
                "lat": float(spot.latitude),
                "lng": float(spot.longitude),
                "difficulty": spot.get_difficulty_display(),
                "country": str(spot.country),
            }
            for spot in spots
        ]

        return JsonResponse(data, safe=False)
