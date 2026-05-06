from django import forms

from .models import Message


class MessageForm(forms.ModelForm):
    """Simple message form shared by direct and session chat."""

    class Meta:
        model = Message
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Write a message...",
                }
            )
        }

    def clean_body(self):
        """Strip surrounding whitespace and reject empty messages."""
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Message cannot be empty.")
        return body

