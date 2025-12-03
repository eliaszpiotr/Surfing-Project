import json
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from spots.models import Spot


class Command(BaseCommand):
    help = "Import surf spots from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Path to JSON file with spots")
        parser.add_argument(
            "--author-email",
            type=str,
            required=True,
            help="Email of the user that will be set as author for imported spots",
        )

    def handle(self, *args, **options):
        json_path = options["json_path"]
        author_email = options["author_email"]

        User = get_user_model()

        # Find author (must exist in DB)
        try:
            author = User.objects.get(email=author_email)
        except User.DoesNotExist:
            raise CommandError(f"User with email {author_email} does not exist")

        # Load JSON file
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {json_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        if not isinstance(data, list):
            raise CommandError("JSON must contain a list of spots")

        created_count = 0
        updated_count = 0

        for item in data:
            name = item.get("name")
            country = item.get("country")

            if not name or not country:
                self.stdout.write(
                    self.style.WARNING("Skipping entry without name or country")
                )
                continue

            # Generate slug from name + country
            base_slug = slugify(name)
            slug = base_slug

            # Ensure slug is unique
            counter = 1
            while Spot.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # You can also decide to update existing spots by name+country:
            spot, created = Spot.objects.update_or_create(
                name=name,
                country=country,
                defaults={
                    "author": author,
                    "slug": slug,
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "location_details": item.get("location_details", ""),
                    "difficulty": item.get("difficulty", Spot.Difficulty.BEGINNER),
                    "surf_break_type": item.get(
                        "surf_break_type", Spot.SurfBreakType.BEACH_BREAK
                    ),
                    "wave_direction": item.get(
                        "wave_direction", Spot.WaveDirection.A_FRAME
                    ),
                    "optimal_swell_direction": item.get(
                        "optimal_swell_direction", ""
                    ),
                    "optimal_wind_direction": item.get(
                        "optimal_wind_direction", ""
                    ),
                    "description": item.get("description", ""),
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import finished. Created: {created_count}, updated: {updated_count}"
            )
        )