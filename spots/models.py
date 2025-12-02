from django.db import models
from django.conf import settings
from django_countries.fields import CountryField
from django.utils.text import slugify


class Spot(models.Model):
    # --- ENUMS (Choices) ---
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
        help_text="Latitude (e.g. 54.608)"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
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
        return f"{self.name} ({self.country})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
