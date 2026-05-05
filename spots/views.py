from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.template.response import TemplateResponse

from .forms import SpotForm, SpotPhotoForm
from .models import Spot
from surf_sessions.models import Session

SPOTS_PER_PAGE = 21


def get_filtered_spots(request):
    """Return a filtered Spot queryset based on GET params (country, difficulty, q)."""
    qs = Spot.objects.all()

    country = request.GET.get("country") or ""
    difficulty = request.GET.get("difficulty") or ""
    query = request.GET.get("q") or ""

    if country:
        qs = qs.filter(country=country)

    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    if query:
        qs = qs.filter(name__icontains=query.strip())

    return qs


def build_spot_detail_context(request, spot, photo_form=None, show_photo_form=False):
    """Build the shared context for a spot detail page and photo upload errors."""
    today = timezone.localdate()
    show_form = request.user.is_authenticated and (
        show_photo_form or request.GET.get("add_photo") == "1"
    )

    return {
        "spot": spot,
        "upcoming_sessions": (
            Session.objects
            .filter(spot=spot, date__gte=today)
            .select_related("organizer")
            .prefetch_related("participants")
            .order_by("date", "start_time")
        ),
        "spot_photos": spot.photos.select_related("author").order_by("-created_at"),
        "photo_form": photo_form if request.user.is_authenticated else None,
        "show_photo_form": show_form,
    }


class SpotAuthorOrStaffRequiredMixin(UserPassesTestMixin):
    """Restrict access to the spot's author or staff members."""

    def test_func(self):
        """Return True if the current user is the spot's author or a staff member."""
        spot = self.get_object()
        user = self.request.user
        return user.is_staff or user == spot.author

    def handle_no_permission(self):
        """Raise 403 for authenticated users; redirect to login for anonymous ones."""
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("You are not allowed to modify this spot.")


class SpotListView(ListView):
    """Paginated, filterable list of all surf spots."""

    model = Spot
    template_name = "spots/spot_list.html"
    context_object_name = "spots"
    paginate_by = SPOTS_PER_PAGE

    def get_queryset(self):
        return get_filtered_spots(self.request)

    def get_context_data(self, **kwargs):
        """Add filter options and active filter values to the template context."""
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

        context["has_next_page"] = context["page_obj"].has_next()

        return context


class SpotListLoadMoreView(View):
    """AJAX endpoint that returns the next page of spot cards as rendered HTML."""

    def get(self, request):
        """Return JSON with rendered HTML fragment and pagination metadata."""
        try:
            page = int(request.GET.get("page", 1))
            if page < 1:
                raise ValueError
        except (ValueError, TypeError):
            return HttpResponseBadRequest("Invalid page number.")

        queryset = get_filtered_spots(request)

        paginator = Paginator(queryset, SPOTS_PER_PAGE)
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
    """Detail page for a single surf spot, including upcoming sessions."""

    model = Spot
    template_name = "spots/spot_detail.html"
    context_object_name = "spot"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        """Add upcoming sessions for this spot to the template context."""
        context = super().get_context_data(**kwargs)
        context.update(
            build_spot_detail_context(
                self.request,
                self.object,
                photo_form=SpotPhotoForm(),
            )
        )
        return context


class SpotCreateView(LoginRequiredMixin, CreateView):
    """Create a new surf spot; the current user becomes the author."""

    model = Spot
    form_class = SpotForm
    template_name = "spots/spot_form.html"

    login_url = "accounts:login"
    redirect_field_name = "next"

    def form_valid(self, form):
        """Assign the current user as author; slug is generated in model.save()."""
        spot = form.save(commit=False)
        spot.author = self.request.user
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
    """Edit an existing surf spot; only the author or staff can access this view."""

    model = Spot
    form_class = SpotForm
    template_name = "spots/spot_form.html"
    context_object_name = "spot"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    login_url = "accounts:login"
    redirect_field_name = "next"

    def form_valid(self, form):
        """Preserve the original author; slug is regenerated in model.save() if empty."""
        spot = form.save(commit=False)
        spot.author = self.get_object().author
        spot.save()
        messages.success(self.request, f"Surf spot '{spot.name}' has been updated successfully!")
        self.object = spot
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("spots:spot_detail", kwargs={"slug": self.object.slug})


class SpotDeleteView(LoginRequiredMixin, SpotAuthorOrStaffRequiredMixin, DeleteView):
    """Delete a surf spot; only the author or staff can perform this action."""

    model = Spot
    template_name = "spots/spot_confirm_delete.html"
    context_object_name = "spot"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("spots:spot_list")

    login_url = "accounts:login"
    redirect_field_name = "next"

    def delete(self, request, *args, **kwargs):
        """Show a success message before delegating deletion to the parent class."""
        spot = self.get_object()
        messages.success(request, f"Surf spot '{spot.name}' has been deleted.")
        return super().delete(request, *args, **kwargs)


class SpotMapDataView(View):
    """Return a JSON array of spots with coordinates for the front-end map."""

    def get(self, request):
        """Serialize spots that have latitude and longitude set."""
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


class SpotPhotoCreateView(LoginRequiredMixin, View):
    """Allow authenticated users to add captioned photos to a surf spot."""

    login_url = "accounts:login"

    def post(self, request, slug):
        """Create a new photo entry or re-render the detail page with errors."""
        spot = get_object_or_404(Spot, slug=slug)
        form = SpotPhotoForm(request.POST, request.FILES)

        if form.is_valid():
            photo = form.save(commit=False)
            photo.spot = spot
            photo.author = request.user
            photo.save()
            messages.success(request, "Photo added successfully!")
            return redirect("spots:spot_detail", slug=spot.slug)

        return TemplateResponse(
            request,
            "spots/spot_detail.html",
            build_spot_detail_context(
                request,
                spot,
                photo_form=form,
                show_photo_form=True,
            ),
            status=200,
        )
