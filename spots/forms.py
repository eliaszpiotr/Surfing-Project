from django import forms
from .models import Spot


class SpotForm(forms.ModelForm):
    class Meta:
        model = Spot
        fields = [
            "name",
            "country",
            "location_details",
            "difficulty",
            "surf_break_type",
            "wave_direction",
            "optimal_swell_direction",
            "optimal_wind_direction",
            "description",
            "image",
            "latitude",
            "longitude",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.Select(attrs={"class": "form-select"}),
            "location_details": forms.TextInput(attrs={"class": "form-control"}),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
            "surf_break_type": forms.Select(attrs={"class": "form-select"}),
            "wave_direction": forms.Select(attrs={"class": "form-select"}),
            "optimal_swell_direction": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "optimal_wind_direction": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control"}),
        }