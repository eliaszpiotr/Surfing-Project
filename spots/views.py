from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.text import slugify
import uuid

from .models import Spot
from .forms import SpotForm


class SpotCreateView(LoginRequiredMixin, CreateView):
    model = Spot
    form_class = SpotForm
    template_name = "spots/spot_form.html"
    success_url = reverse_lazy("home")

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