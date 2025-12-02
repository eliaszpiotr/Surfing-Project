from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
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
    success_url = reverse_lazy("spots:spot_list")

    login_url = "login"
    redirect_field_name = "next"

    def form_valid(self, form):
        spot = form.save(commit=False)
        spot.author = self.request.user

        if not spot.slug:
            spot.slug = slugify(spot.name) + "-" + str(uuid.uuid4())[:8]

        spot.save()
        messages.success(self.request, f"Surf spot '{spot.name}' has been added successfully!")
        return super().form_valid(form)


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