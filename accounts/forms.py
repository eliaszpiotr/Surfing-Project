from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import UserProfile


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    Registration form for new users.
    Uses email as the main identifier and requires a username and password.
    """

    class Meta:
        model = User
        # Password fields (password1, password2) are provided by UserCreationForm,
        # so we only list email and username here.
        fields = ("email", "username")


class CustomAuthenticationForm(AuthenticationForm):
    """
    Login form for users.
    Uses the custom user model.
    """

    class Meta:
        model = User
        fields = ("username", "password")


class UserProfileForm(forms.ModelForm):
    """
    Form for editing the user's profile data.
    """

    class Meta:
        model = UserProfile
        fields = ("bio", "country", "profile_picture")