import io

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django_countries.fields import CountryField
from django.utils.text import slugify
from PIL import Image


def validate_image_content(file):
    """Verify that a freshly uploaded file is a genuine image."""
    if not isinstance(file, UploadedFile):
        return
    try:
        data = file.read()
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise ValidationError(
            "Uploaded file is not a valid image. "
            "Please upload a JPG, PNG or WebP file."
        )
    finally:
        if hasattr(file, "seek"):
            file.seek(0)


class Spot(models.Model):
    """A surf spot with location, surf characteristics, and optional media."""

    # --- Choices ---
    class Difficulty(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'
        PRO = 'pro', 'Pro Only'

    class SurfBreakType(models.TextChoices):
        BEACH_BREAK = 'beach_break', 'Beach Break'
        REEF_BREAK = 'reef_break', 'Reef Break'
        POINT_BREAK = 'point_break', 'Point Break'
        RIVERMOUTH = 'rivermouth', 'Rivermouth'
        JETTY_PIER = 'jetty_pier', 'Jetty / Pier'

    class WaveDirection(models.TextChoices):
        RIGHT = 'right', 'Right'
        LEFT = 'left', 'Left'
        A_FRAME = 'a_frame', 'A-Frame'

    # --- BASIC IDENTITY ---
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='spots'
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    country = CountryField()

    # --- LOCATION ---
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude (e.g. 54.608)"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude (e.g. 18.800)"
    )
    location_details = models.CharField(
        max_length=255,
        blank=True,
        help_text="Specific details (e.g. 'Entrance no. 14, park near the hotel')"
    )

    # --- SURF DETAILS ---
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER
    )
    surf_break_type = models.CharField(
        max_length=20,
        choices=SurfBreakType.choices,
        default=SurfBreakType.BEACH_BREAK
    )
    wave_direction = models.CharField(
        max_length=20,
        choices=WaveDirection.choices,
        default=WaveDirection.A_FRAME
    )

    # --- BEST CONDITIONS ---
    optimal_swell_direction = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. NW, N (Direction from which the swell works best)"
    )
    optimal_wind_direction = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. SE (Offshore wind direction)"
    )

    description = models.TextField(blank=True, help_text="General description of the vibe and spot")

    # --- MEDIA ---
    image = models.ImageField(upload_to='spots_images/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return the spot name together with its country code."""
        return f"{self.name} ({self.country})"

    def save(self, *args, **kwargs):
        """Auto-generate a unique slug from the spot name before saving."""
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            # Ensure slug uniqueness without relying on views
            while Spot.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']


class SpotPhoto(models.Model):
    """A user-submitted photo attached to a surf spot."""

    spot = models.ForeignKey(
        Spot,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="spot_photos",
    )
    image = models.ImageField(
        upload_to="spot_gallery/",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_image_content,
        ],
    )
    caption = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        """Enforce a 10 MB size limit on uploaded spot photos."""
        super().clean()
        if self.image and hasattr(self.image, "size") and self.image.size > 10 * 1024 * 1024:
            raise ValidationError({"image": "Image must be under 10MB."})

    def __str__(self):
        """Return a short label for the photo entry."""
        return f"{self.spot.name}: {self.caption[:40]}"
