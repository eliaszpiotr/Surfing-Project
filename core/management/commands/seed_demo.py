import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw

from spots.models import Spot, SpotPhoto
from surf_sessions.models import Session


DEMO_SPOTS = [
    {
        "name": "Hel - Kuznica",
        "country": "PL",
        "latitude": 54.608,
        "longitude": 18.8,
        "difficulty": "beginner",
        "surf_break_type": "beach_break",
        "wave_direction": "a_frame",
        "optimal_swell_direction": "N, NW",
        "optimal_wind_direction": "SE",
        "location_details": "Entrance 14, parking near hotel",
        "description": "Easy beach break, good for beginners.",
    },
    {
        "name": "Jastarnia Reef",
        "country": "PL",
        "latitude": 54.7,
        "longitude": 18.67,
        "difficulty": "advanced",
        "surf_break_type": "reef_break",
        "wave_direction": "right",
        "optimal_swell_direction": "N",
        "optimal_wind_direction": "S",
        "location_details": "Offshore near the port",
        "description": "Shallow reef, only for experienced surfers.",
    },
    {
        "name": "Banzai Pipeline",
        "country": "US",
        "latitude": 21.664,
        "longitude": -158.053,
        "difficulty": "pro",
        "surf_break_type": "reef_break",
        "wave_direction": "left",
        "optimal_swell_direction": "W, NW",
        "optimal_wind_direction": "E",
        "location_details": "Oahu, North Shore",
        "description": "The world's most famous and deadly wave.",
    },
    {
        "name": "Teahupo'o",
        "country": "PF",
        "latitude": -17.847,
        "longitude": -149.267,
        "difficulty": "pro",
        "surf_break_type": "reef_break",
        "wave_direction": "left",
        "optimal_swell_direction": "S, SW",
        "optimal_wind_direction": "NE",
        "location_details": "Tahiti Iti",
        "description": "Heaviest wave in the world, breaking over shallow coral.",
    },
    {
        "name": "Uluwatu",
        "country": "ID",
        "latitude": -8.814,
        "longitude": 115.088,
        "difficulty": "advanced",
        "surf_break_type": "reef_break",
        "wave_direction": "left",
        "optimal_swell_direction": "S, SW",
        "optimal_wind_direction": "SE",
        "location_details": "Bali, Bukit Peninsula",
        "description": "Iconic cliffs and consistent long rides.",
    },
    {
        "name": "Superbank",
        "country": "AU",
        "latitude": -28.162,
        "longitude": 153.55,
        "difficulty": "advanced",
        "surf_break_type": "point_break",
        "wave_direction": "right",
        "optimal_swell_direction": "E, SE",
        "optimal_wind_direction": "SW",
        "location_details": "Gold Coast, Snapper Rocks",
        "description": "Crowded but perfect endless barrel.",
    },
    {
        "name": "Jeffreys Bay",
        "country": "ZA",
        "latitude": -34.034,
        "longitude": 24.937,
        "difficulty": "advanced",
        "surf_break_type": "point_break",
        "wave_direction": "right",
        "optimal_swell_direction": "SW",
        "optimal_wind_direction": "SW",
        "location_details": "Eastern Cape",
        "description": "Fast, long right-hander, home of the J-Bay Open.",
    },
    {
        "name": "Mavericks",
        "country": "US",
        "latitude": 37.495,
        "longitude": -122.5,
        "difficulty": "pro",
        "surf_break_type": "reef_break",
        "wave_direction": "right",
        "optimal_swell_direction": "NW, W",
        "optimal_wind_direction": "E",
        "location_details": "California, Half Moon Bay",
        "description": "Cold water big wave spot, scary and powerful.",
    },
    {
        "name": "Nazare",
        "country": "PT",
        "latitude": 39.601,
        "longitude": -9.071,
        "difficulty": "pro",
        "surf_break_type": "beach_break",
        "wave_direction": "a_frame",
        "optimal_swell_direction": "W, NW",
        "optimal_wind_direction": "E, SE",
        "location_details": "Praia do Norte",
        "description": "Guinness Record holder for biggest waves surfed.",
    },
    {
        "name": "La Graviere",
        "country": "FR",
        "latitude": 43.669,
        "longitude": -1.44,
        "difficulty": "advanced",
        "surf_break_type": "beach_break",
        "wave_direction": "a_frame",
        "optimal_swell_direction": "W, NW",
        "optimal_wind_direction": "E",
        "location_details": "Hossegor",
        "description": "Heavy shorebreak barrels, world class beach break.",
    },
    {
        "name": "Mundaka",
        "country": "ES",
        "latitude": 43.408,
        "longitude": -2.697,
        "difficulty": "advanced",
        "surf_break_type": "rivermouth_break",
        "wave_direction": "left",
        "optimal_swell_direction": "NW",
        "optimal_wind_direction": "S, SW",
        "location_details": "Basque Country",
        "description": "Europe's best left, fast and tubular.",
    },
    {
        "name": "Cloudbreak",
        "country": "FJ",
        "latitude": -17.857,
        "longitude": 177.203,
        "difficulty": "pro",
        "surf_break_type": "reef_break",
        "wave_direction": "left",
        "optimal_swell_direction": "S, SW",
        "optimal_wind_direction": "E",
        "location_details": "Tavarua Island",
        "description": "Fast, hollow, open ocean reef pass.",
    },
]


class Command(BaseCommand):
    help = "Seed demo users, spots, sessions, and photos for local or Docker demos."

    def handle(self, *args, **options):
        """Populate the database with deterministic demo data without duplicating rows."""
        users = self._seed_users()
        spots = self._seed_spots(users)
        self._seed_sessions(users, spots)
        self._seed_photos(users, spots)
        self.stdout.write(self.style.SUCCESS("Demo data is ready."))

    def _seed_users(self):
        """Create or update a small set of demo users."""
        User = get_user_model()
        user_specs = [
            {
                "email": "demo.anna@example.com",
                "username": "anna",
                "first_name": "Anna",
                "last_name": "Nowak",
            },
            {
                "email": "demo.marc@example.com",
                "username": "marc",
                "first_name": "Marc",
                "last_name": "Silva",
            },
            {
                "email": "demo.kai@example.com",
                "username": "kai",
                "first_name": "Kai",
                "last_name": "Tanaka",
            },
        ]

        users = []
        for index, spec in enumerate(user_specs):
            user, _ = User.objects.update_or_create(
                email=spec["email"],
                defaults={
                    "username": spec["username"],
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                },
            )
            user.set_password("pass1234")
            user.save(update_fields=["password"])
            profile = user.profile
            if not self._field_file_exists(profile.profile_picture):
                avatar_bytes = self._build_demo_avatar(user.username, index)
                profile.profile_picture.save(
                    f"demo-profile-{user.username}.jpg",
                    ContentFile(avatar_bytes),
                    save=True,
                )
            users.append(user)

        return users

    def _seed_spots(self, users):
        """Load a curated set of in-code demo spots."""
        spots = []
        for index, item in enumerate(DEMO_SPOTS):
            spot, _ = Spot.objects.update_or_create(
                name=item["name"],
                country=item["country"],
                defaults={
                    "author": users[index % len(users)],
                    "slug": "",
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "location_details": item.get("location_details", ""),
                    "difficulty": item.get("difficulty", Spot.Difficulty.BEGINNER),
                    "surf_break_type": item.get("surf_break_type", Spot.SurfBreakType.BEACH_BREAK),
                    "wave_direction": item.get("wave_direction", Spot.WaveDirection.A_FRAME),
                    "optimal_swell_direction": item.get("optimal_swell_direction", ""),
                    "optimal_wind_direction": item.get("optimal_wind_direction", ""),
                    "description": item.get("description", ""),
                },
            )
            spots.append(spot)

        return spots

    def _seed_sessions(self, users, spots):
        """Create a handful of future and past sessions around the imported demo spots."""
        today = timezone.localdate()
        session_specs = [
            ("Dawn Patrol", spots[0], users[0], today + timedelta(days=1), "06:30", "08:30", 4, "Coffee after the session."),
            ("Sunset Glass-Off", spots[1], users[1], today + timedelta(days=2), "18:00", "20:00", 6, "Bring a thicker wetsuit."),
            ("Weekend Longboard", spots[2], users[2], today + timedelta(days=4), "09:00", "11:30", None, "Beginner-friendly meetup."),
            ("Storm Chase", spots[3], users[0], today + timedelta(days=6), "07:30", "10:00", 5, "Check forecast before joining."),
            ("After Work Surf", spots[4], users[1], today + timedelta(days=8), "17:30", "19:00", 3, "Quick evening session."),
            ("Spring Session", spots[5], users[2], today - timedelta(days=3), "08:00", "10:00", 4, "Past session for profile history."),
        ]

        for index, (name, spot, organizer, date, start_time, end_time, max_participants, note) in enumerate(session_specs):
            session, _ = Session.objects.update_or_create(
                spot=spot,
                organizer=organizer,
                name=name,
                date=date,
                defaults={
                    "start_time": start_time,
                    "end_time": end_time,
                    "max_participants": max_participants,
                    "note": note,
                },
            )
            session.participants.add(organizer)
            extra_user = users[(index + 1) % len(users)]
            if session.can_join(extra_user):
                session.participants.add(extra_user)

    def _seed_photos(self, users, spots):
        """Attach a few generated photos so the spot gallery is not empty."""
        photo_specs = [
            (spots[0], users[0], "Cold sunrise lines", "#1f6f8b"),
            (spots[1], users[1], "Windy but fun", "#355c7d"),
            (spots[2], users[2], "Long clean walls", "#f67280"),
        ]

        for index, (spot, author, caption, color) in enumerate(photo_specs):
            photo, created = SpotPhoto.objects.get_or_create(
                spot=spot,
                author=author,
                caption=caption,
            )
            if created or not self._field_file_exists(photo.image):
                image_bytes = self._build_demo_image(spot.name, color)
                file_name = f"demo-spot-{index + 1}.jpg"
                photo.image.save(file_name, ContentFile(image_bytes), save=True)

    def _build_demo_image(self, title, color):
        """Generate a simple placeholder image for demo galleries."""
        canvas = Image.new("RGB", (1200, 800), color=color)
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((70, 70, 1130, 730), outline="white", width=6)
        draw.text((110, 120), title, fill="white")
        draw.text((110, 180), "Surfing Project demo photo", fill="white")

        buffer = io.BytesIO()
        canvas.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue()

    def _build_demo_avatar(self, username, index):
        """Generate a simple avatar image so demo profiles always have media files."""
        palette = ["#1f6f8b", "#355c7d", "#f67280"]
        canvas = Image.new("RGB", (320, 320), color=palette[index % len(palette)])
        draw = ImageDraw.Draw(canvas)
        draw.ellipse((52, 52, 268, 268), outline="white", width=10)
        draw.text((136, 138), username[:1].upper(), fill="white")

        buffer = io.BytesIO()
        canvas.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue()

    def _field_file_exists(self, field_file):
        """Return True only when the field has a name and the file exists in storage."""
        return bool(
            field_file
            and getattr(field_file, "name", "")
            and field_file.storage.exists(field_file.name)
        )
