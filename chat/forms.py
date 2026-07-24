from django import forms

from .models import Message
from surfingproject.uploads import normalize_uploaded_image


class MessageForm(forms.ModelForm):
    """Simple message form shared by direct and session chat."""

    class Meta:
        model = Message
        fields = ["body", "image"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Write a message...",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }

    def clean_body(self):
        """Strip surrounding whitespace and reject empty messages."""
        return self.cleaned_data["body"].strip()

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        return normalize_uploaded_image(image, "chat_messages")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("body") and not cleaned_data.get("image"):
            raise forms.ValidationError("Message cannot be empty.")
        return cleaned_data
