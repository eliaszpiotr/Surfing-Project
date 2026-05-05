from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Session


class SessionForm(forms.ModelForm):
    """Form for creating and editing a surf session."""

    class Meta:
        model = Session
        fields = ["name", "date", "start_time", "end_time", "max_participants", "note"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Session name (e.g. Sunrise surf)", "required": True}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "end_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "max_participants": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "note": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        """Apply Bootstrap styling to the spot select widget if present."""
        super().__init__(*args, **kwargs)

        if "spot" in self.fields:
            self.fields["spot"].widget.attrs.update({"class": "form-select"})

    def clean_date(self):
        """Reject past dates for new sessions; allow editing sessions that already have one."""
        date = self.cleaned_data.get("date")
        if date and not self.instance.pk and date < timezone.localdate():
            raise ValidationError("Cannot create a session for a past date.")
        return date

    def clean(self):
        """Ensure end time is strictly after start time when both are provided."""
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time and end_time <= start_time:
            raise ValidationError({"end_time": "End time must be after start time."})

        return cleaned_data