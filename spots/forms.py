import io

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image

from .models import Spot


def _validate_image_content(image_file):
    """Raise ValidationError if a freshly uploaded file is not a valid image according to Pillow."""
    if not isinstance(image_file, UploadedFile):
        return
    try:
        data = image_file.read()
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise ValidationError(
            "Uploaded file is not a valid image. "
            "Please upload a JPG, PNG or WebP file."
        )
    finally:
        if hasattr(image_file, "seek"):
            image_file.seek(0)


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
        if not image or not hasattr(image, "size"):
            return image
        if image.size > 10 * 1024 * 1024:
            raise ValidationError("Image must be under 10MB.")
        _validate_image_content(image)
        return image

    def clean(self):
        """Require both latitude and longitude to be set, or both to be empty."""
        cleaned_data = super().clean()
        lat = cleaned_data.get("latitude")
        lng = cleaned_data.get("longitude")

        if bool(lat) != bool(lng):
            raise ValidationError("Provide both latitude and longitude, or leave both empty.")

        return cleaned_data