from django import forms
from .models import Session


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ["name","date", "start_time", "end_time", "max_participants", "note"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Session name (e.g. Sunrise surf)", "required": True}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "end_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "max_participants": forms.NumberInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Style spot select
        if "spot" in self.fields:
            self.fields["spot"].widget.attrs.update({"class": "form-select"})

        # # If spot is prefilled (coming from spot detail), hide the field
        # initial_spot = self.initial.get("spot") or getattr(self.instance, "spot", None)
        # if initial_spot is not None:
        #     self.fields["spot"].widget = forms.HiddenInput()