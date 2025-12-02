from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
import uuid
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views import View

from .forms import SpotForm
from .models import Spot
from surf_sessions.models import Session


class SpotAuthorOrStaffRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        spot = self.get_object()
        user = self.request.user
        return user.is_staff or user == spot.author

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You are not allowed to modify this spot.")


class SpotListView(ListView):
    model = Spot
    template_name = "spots/spot_list.html"
    context_object_name = "spots"
    paginate_by = 21

    def get_filtered_queryset(self):
        qs = Spot.objects.all()

        country = self.request.GET.get("country") or ""
        difficulty = self.request.GET.get("difficulty") or ""
        query = self.request.GET.get("q") or ""

        if country:
            qs = qs.filter(country=country)

        if difficulty:
            qs = qs.filter(difficulty=difficulty)

        if query:
            qs = qs.filter(name__icontains=query.strip())

        return qs

    def get_queryset(self):
        return self.get_filtered_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["countries"] = (
            Spot.objects.exclude(country__isnull=True)
            .exclude(country__exact="")
            .values_list("country", flat=True)
            .distinct()
            .order_by("country")
        )
        context["difficulties"] = Spot.Difficulty.choices

        context["current_country"] = self.request.GET.get("country", "")
        context["current_difficulty"] = self.request.GET.get("difficulty", "")
        context["current_query"] = self.request.GET.get("q", "")

        # Needed for load-more initial state
        context["has_next_page"] = context["page_obj"].has_next()

        return context


class SpotListLoadMoreView(View):

    def get(self, request):
        page = int(request.GET.get("page", 1))

        # Reuse the filtering logic from SpotListView
        list_view = SpotListView()
        list_view.request = request
        queryset = list_view.get_filtered_queryset()

        paginator = Paginator(queryset, 21)
        page_obj = paginator.get_page(page)

        html = render_to_string(
            "spots/_spot_cards.html",
            {"spots": page_obj.object_list},
            request=request,
        )

        return JsonResponse(
            {
                "html": html,
                "has_next": page_obj.has_next(),
                "next_page": page + 1,
            }
        )


class SpotDetailView(DetailView):
    model = Spot
    template_name = "spots/spot_detail.html"
    context_object_name = "spot"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        context["upcoming_sessions"] = (
            Session.objects
            .filter(spot=self.object, date__gte=today)
            .order_by("date", "start_time")
        )
        return context


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


class SpotUpdateView(LoginRequiredMixin, SpotAuthorOrStaffRequiredMixin, UpdateView):
    model = Spot
    form_class = SpotForm
    template_name = "spots/spot_form.html"
    context_object_name = "spot"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    login_url = "login"
    redirect_field_name = "next"

    def form_valid(self, form):
        spot = form.save(commit=False)
        spot.author = self.get_object().author
        if not spot.slug:
            spot.slug = slugify(spot.name) + "-" + str(uuid.uuid4())[:8]

        spot.save()
        messages.success(self.request, f"Surf spot '{spot.name}' has been updated successfully!")
        self.object = spot
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("spots:spot_detail", kwargs={"slug": self.object.slug})


class SpotDeleteView(LoginRequiredMixin, SpotAuthorOrStaffRequiredMixin, DeleteView):
    model = Spot
    template_name = "spots/spot_confirm_delete.html"
    context_object_name = "spot"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("spots:spot_list")

    login_url = "login"
    redirect_field_name = "next"

    def delete(self, request, *args, **kwargs):
        spot = self.get_object()
        messages.success(request, f"Surf spot '{spot.name}' has been deleted.")
        return super().delete(request, *args, **kwargs)


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
