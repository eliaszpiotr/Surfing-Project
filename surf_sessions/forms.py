from django import forms

from .models import Session


class SessionForm(forms.ModelForm):
    """
    Form for creating/updating a surf session.

    The Spot is NOT chosen in the form – it is injected in the view
    (we always create a session for a given spot).
    """

    class Meta:
        model = Session
        fields = [
            "date",
            "start_time",
            "end_time",
            "max_participants",
            "note",
        ]
        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "start_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),
            "end_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),
            "max_participants": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Meeting point, expected level, extra info...",
                }
            ),
        }