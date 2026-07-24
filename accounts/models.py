from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django_countries.fields import CountryField

from .managers import CustomUserManager
from django.conf import settings
from core.validators import (
    ALLOWED_IMAGE_EXTENSIONS,
    validate_uploaded_image,
    validate_uploaded_image as validate_image_content,
)
from surfingproject.uploads import (
    profile_picture_upload_path,
)


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    following = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="followers",
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the user's full name as a single string."""
        return f"{self.first_name} {self.last_name}"

    @property
    def followers_count(self):
        """Return the number of users following this account."""
        return self.followers.count()

    @property
    def following_count(self):
        """Return the number of accounts this user follows."""
        return self.following.count()

    def is_following(self, other_user):
        """Return True when this user follows the given user."""
        if not other_user or not self.is_authenticated:
            return False
        return self.following.filter(pk=other_user.pk).exists()


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(blank=True)
    country = CountryField(blank_label='(select country)', blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_path,
        default="profile_pictures/default_profile.jpg",
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS),
            validate_uploaded_image,
        ],
    )

    def clean(self):
        """Enforce a 5 MB size limit on profile pictures."""
        super().clean()
        if not self.profile_picture:
            return

        max_size = 5 * 1024 * 1024
        uploaded = getattr(self.profile_picture, "_file", None)
        if uploaded:
            try:
                validate_uploaded_image(uploaded, max_size=max_size)
            except ValidationError as exc:
                raise ValidationError({"profile_picture": exc.messages})
            return

        try:
            if hasattr(self.profile_picture, "size") and self.profile_picture.size > max_size:
                raise ValidationError({"profile_picture": "Image must be under 5MB."})
        except OSError:
            return

    def __str__(self):
        """Return the linked user's username, falling back to email."""
        username = getattr(self.user, "username", None)
        return username or getattr(self.user, "email", "Profile")
