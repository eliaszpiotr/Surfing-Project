from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.conf import settings
from django_countries.fields import CountryField
from django.utils.text import slugify


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
