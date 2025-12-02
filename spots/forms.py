from django import forms
from .models import Spot


class SpotForm(forms.ModelForm):
    class Meta:
        model = Spot
        exclude = ("author", "slug")
        fields = [
            "name",
            "country",
            "latitude",
            "longitude",
            "location_details",
            "difficulty",
            "surf_break_type",
            "wave_direction",
            "optimal_swell_direction",
            "optimal_wind_direction",
            "description",
            "image",
        ]