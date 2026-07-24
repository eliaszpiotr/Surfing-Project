from django import forms
from django.core.exceptions import ValidationError

from .models import Spot, SpotPhoto
from surfingproject.uploads import normalize_uploaded_image


class SpotForm(forms.ModelForm):
    """Form for creating and editing a surf spot."""
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
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def clean_image(self):
        """Enforce 10 MB size limit and verify that the uploaded file is a real image."""
        image = self.cleaned_data.get("image")
        if not image:
            return image
        return normalize_uploaded_image(image, "spots_images", max_size=10 * 1024 * 1024)

    def clean(self):
        """Require both latitude and longitude to be set, or both to be empty."""
        cleaned_data = super().clean()
        lat = cleaned_data.get("latitude")
        lng = cleaned_data.get("longitude")

        if bool(lat) != bool(lng):
            raise ValidationError("Provide both latitude and longitude, or leave both empty.")

        return cleaned_data


class SpotPhotoForm(forms.ModelForm):
    """Form for adding a captioned photo to an existing spot."""

    class Meta:
        model = SpotPhoto
        fields = ["image", "caption"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "caption": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Write a short caption for this photo",
                }
            ),
        }

    def clean_image(self):
        """Enforce image validation consistently at form level."""
        image = self.cleaned_data.get("image")
        if not image:
            return image
        return normalize_uploaded_image(image, "spot_gallery", max_size=10 * 1024 * 1024)
