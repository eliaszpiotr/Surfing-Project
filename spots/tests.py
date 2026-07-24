import io
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from spots.forms import SpotForm, SpotPhotoForm
from spots.models import Spot, SpotPhoto
from surf_sessions.models import Session

User = get_user_model()


def make_image_upload(name="wave.jpg", fmt="JPEG"):
    """Create a small in-memory image upload for spot tests."""
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color="navy").save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def create_user(email, username, is_staff=False):
    """Create a user for spot-related tests."""
    return User.objects.create_user(
        email=email,
        username=username,
        password="pass1234",
        is_staff=is_staff,
    )


def create_spot(author, name, country="PT", difficulty=Spot.Difficulty.BEGINNER, latitude=38.0, longitude=-9.0):
    """Create a reusable spot object with optional coordinates."""
    return Spot.objects.create(
        name=name,
        author=author,
        country=country,
        difficulty=difficulty,
        latitude=latitude,
        longitude=longitude,
    )


@pytest.fixture
def owner(db):
    return create_user("owner@test.com", "spot_owner")


@pytest.fixture
def user(db):
    return create_user("photo@test.com", "photo_user")


@pytest.fixture
def spot(owner):
    return create_spot(
        owner,
        name="Hossegor",
        country="FR",
        latitude=43.665,
        longitude=-1.444,
    )


@pytest.mark.django_db
def test_authenticated_user_can_add_photo_to_spot(client, user, spot):
    client.force_login(user)

    response = client.post(
        reverse("spots:spot_photo_create", args=[spot.slug]),
        {
            "caption": "Clean evening lines",
            "image": make_image_upload(),
        },
        follow=False,
    )

    assert response.status_code == 302
    photo = SpotPhoto.objects.get(spot=spot)
    assert photo.author == user
    assert photo.caption == "Clean evening lines"


@pytest.mark.django_db
@override_settings(
    RATE_LIMITS={
        "upload_user": {"limit": 1, "window": 60},
    }
)
def test_spot_photo_upload_is_rate_limited(client, user, spot):
    cache.clear()
    client.force_login(user)
    url = reverse("spots:spot_photo_create", args=[spot.slug])

    assert client.post(
        url,
        {
            "caption": "First",
            "image": make_image_upload(name="first.jpg"),
        },
    ).status_code == 302

    response = client.post(
        url,
        {
            "caption": "Second",
            "image": make_image_upload(name="second.jpg"),
        },
    )

    assert response.status_code == 429
    assert SpotPhoto.objects.filter(spot=spot).count() == 1
    cache.clear()


@pytest.mark.django_db
def test_anonymous_user_is_redirected_when_adding_photo(client, spot):
    response = client.post(
        reverse("spots:spot_photo_create", args=[spot.slug]),
        {
            "caption": "Anonymous upload",
            "image": make_image_upload(),
        },
        follow=False,
    )

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]
    assert SpotPhoto.objects.count() == 0


@pytest.mark.django_db
def test_invalid_photo_submission_rerenders_detail_with_errors(client, user, spot):
    client.force_login(user)

    response = client.post(
        reverse("spots:spot_photo_create", args=[spot.slug]),
        {
            "caption": "",
            "image": SimpleUploadedFile("not-image.jpg", b"not really an image", content_type="image/jpeg"),
        },
        follow=False,
    )

    assert response.status_code == 200
    assert SpotPhoto.objects.count() == 0
    assert "photo_form" in response.context
    assert response.context["show_photo_form"] is True


@pytest.mark.django_db
def test_spot_generates_unique_slugs_for_duplicate_names():
    author = create_user("slug@test.com", "slugger")

    first = Spot.objects.create(name="Mundaka", author=author, country="ES")
    second = Spot.objects.create(name="Mundaka", author=author, country="PT")

    assert first.slug == "mundaka"
    assert second.slug == "mundaka-1"


@pytest.mark.django_db
def test_spot_photo_clean_rejects_images_over_ten_mb():
    author = create_user("photo-size@test.com", "photosize")
    spot = Spot.objects.create(name="Nazare", author=author, country="PT")
    photo = SpotPhoto(spot=spot, author=author, caption="Big wave")
    photo.image.name = "spot_gallery/big-wave.jpg"
    photo.image.storage.size = lambda name: 10 * 1024 * 1024 + 1

    with pytest.raises(ValidationError):
        photo.clean()


def test_spot_form_rejects_only_one_coordinate():
    form = SpotForm(
        data={
            "name": "Hel",
            "country": "PL",
            "difficulty": "beginner",
            "surf_break_type": "beach_break",
            "wave_direction": "a_frame",
            "latitude": "54.608000",
            "longitude": "",
        }
    )

    assert not form.is_valid()
    assert "__all__" in form.errors


def test_spot_form_accepts_both_coordinates():
    form = SpotForm(
        data={
            "name": "Hel",
            "country": "PL",
            "difficulty": "beginner",
            "surf_break_type": "beach_break",
            "wave_direction": "a_frame",
            "latitude": "54.608000",
            "longitude": "18.800000",
        }
    )

    assert form.is_valid()


def test_spot_form_rejects_invalid_image_content():
    form = SpotForm(
        data={
            "name": "Hel",
            "country": "PL",
            "difficulty": "beginner",
            "surf_break_type": "beach_break",
            "wave_direction": "a_frame",
            "latitude": "",
            "longitude": "",
        },
        files={
            "image": SimpleUploadedFile("fake.jpg", b"not-an-image", content_type="image/jpeg"),
        },
    )

    assert not form.is_valid()
    assert "image" in form.errors


def test_spot_photo_form_accepts_valid_image_and_caption():
    form = SpotPhotoForm(
        data={"caption": "Sunset lineup"},
        files={"image": make_image_upload()},
    )

    assert form.is_valid()


@pytest.mark.django_db
def test_spot_list_filters_by_country_difficulty_and_query(client):
    author = create_user("filters@test.com", "filters")
    matching = create_spot(author, "Supertubos", country="PT", difficulty=Spot.Difficulty.ADVANCED)
    create_spot(author, "Mundaka", country="ES", difficulty=Spot.Difficulty.ADVANCED)
    create_spot(author, "Baleal", country="PT", difficulty=Spot.Difficulty.BEGINNER)

    response = client.get(
        reverse("spots:spot_list"),
        {
            "country": "PT",
            "difficulty": Spot.Difficulty.ADVANCED,
            "q": "super",
        },
    )

    assert response.status_code == 200
    assert list(response.context["spots"]) == [matching]


@pytest.mark.django_db
def test_spot_load_more_rejects_invalid_page(client):
    response = client.get(reverse("spots:spot_list_load_more"), {"page": "zero"})

    assert response.status_code == 400


@pytest.mark.django_db
def test_spot_load_more_returns_second_page_html(client):
    author = create_user("pages@test.com", "pages")
    for index in range(22):
        create_spot(author, f"Spot {index}", latitude=40 + index, longitude=-8 - index)

    response = client.get(reverse("spots:spot_list_load_more"), {"page": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_next"] is False
    assert "Spot 0" in payload["html"] or "Spot 1" in payload["html"]


@pytest.mark.django_db
def test_spot_detail_shows_future_sessions_and_hides_photo_form_by_default_for_authenticated_user(client):
    author = create_user("detail@test.com", "detail")
    viewer = create_user("viewer@test.com", "viewer")
    detailed_spot = create_spot(author, "Lofoten", country="NO")
    today = timezone.localdate()

    future_session = Session.objects.create(
        name="Arctic dawn patrol",
        spot=detailed_spot,
        organizer=author,
        date=today + timedelta(days=2),
        start_time="06:00",
    )
    Session.objects.create(
        name="Old surf",
        spot=detailed_spot,
        organizer=author,
        date=today - timedelta(days=2),
        start_time="06:00",
    )

    client.force_login(viewer)
    response = client.get(reverse("spots:spot_detail", args=[detailed_spot.slug]))

    assert response.status_code == 200
    assert list(response.context["upcoming_sessions"]) == [future_session]
    assert response.context["photo_form"] is not None
    assert response.context["show_photo_form"] is False


@pytest.mark.django_db
def test_spot_detail_can_show_photo_form_on_demand(client):
    author = create_user("detail-form@test.com", "detailform")
    viewer = create_user("detail-viewer@test.com", "detailviewer")
    detailed_spot = create_spot(author, "Mavericks", country="US")

    client.force_login(viewer)
    response = client.get(reverse("spots:spot_detail", args=[detailed_spot.slug]), {"add_photo": 1})

    assert response.status_code == 200
    assert response.context["photo_form"] is not None
    assert response.context["show_photo_form"] is True


@pytest.mark.django_db
def test_spot_detail_hides_photo_form_for_anonymous_user(client):
    author = create_user("anon-detail@test.com", "anondetail")
    detailed_spot = create_spot(author, "Jeffreys Bay", country="ZA")

    response = client.get(reverse("spots:spot_detail", args=[detailed_spot.slug]))

    assert response.status_code == 200
    assert response.context["photo_form"] is None
    assert response.context["show_photo_form"] is False


@pytest.mark.django_db
def test_spot_detail_shows_more_button_when_gallery_has_more_than_four_photos(client, user, spot):
    for index in range(5):
        SpotPhoto.objects.create(
            spot=spot,
            author=user,
            caption=f"Photo {index}",
            image=make_image_upload(name=f"wave-{index}.jpg"),
        )

    response = client.get(reverse("spots:spot_detail", args=[spot.slug]))

    assert response.status_code == 200
    assert "Show more photos" in response.content.decode()


@pytest.mark.django_db
def test_spot_create_requires_login(client):
    response = client.get(reverse("spots:spot_create"), follow=False)

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]


@pytest.mark.django_db
def test_authenticated_user_can_create_spot_and_becomes_author(client):
    user = create_user("creator@test.com", "creator")
    client.force_login(user)

    response = client.post(
        reverse("spots:spot_create"),
        {
            "name": "Taghazout",
            "country": "MA",
            "location_details": "Anchor Point",
            "difficulty": Spot.Difficulty.INTERMEDIATE,
            "surf_break_type": Spot.SurfBreakType.POINT_BREAK,
            "wave_direction": Spot.WaveDirection.RIGHT,
            "optimal_swell_direction": "NW",
            "optimal_wind_direction": "E",
            "description": "Long right-hand point break",
            "latitude": "30.544000",
            "longitude": "-9.707000",
        },
        follow=False,
    )

    created_spot = Spot.objects.get(name="Taghazout")
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("spots:spot_detail", args=[created_spot.slug])
    assert created_spot.author == user


@pytest.mark.django_db
def test_non_author_cannot_update_spot(client):
    author = create_user("author@test.com", "author")
    other_user = create_user("other@test.com", "other")
    editable_spot = create_spot(author, "Bundoran", country="IE")

    client.force_login(other_user)
    response = client.post(
        reverse("spots:spot_update", args=[editable_spot.slug]),
        {
            "name": "Bundoran edited",
            "country": "IE",
            "difficulty": editable_spot.difficulty,
            "surf_break_type": editable_spot.surf_break_type,
            "wave_direction": editable_spot.wave_direction,
            "location_details": "",
            "optimal_swell_direction": "",
            "optimal_wind_direction": "",
            "description": "",
            "latitude": "38.000000",
            "longitude": "-9.000000",
        },
        follow=False,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_user_can_update_other_users_spot(client):
    author = create_user("spot-author@test.com", "spotauthor")
    staff_user = create_user("staff@test.com", "staff", is_staff=True)
    editable_spot = create_spot(author, "Uluwatu", country="ID")

    client.force_login(staff_user)
    response = client.post(
        reverse("spots:spot_update", args=[editable_spot.slug]),
        {
            "name": "Uluwatu updated",
            "country": "ID",
            "difficulty": Spot.Difficulty.ADVANCED,
            "surf_break_type": Spot.SurfBreakType.REEF_BREAK,
            "wave_direction": Spot.WaveDirection.LEFT,
            "location_details": "",
            "optimal_swell_direction": "SW",
            "optimal_wind_direction": "E",
            "description": "Updated by staff",
            "latitude": "-8.818000",
            "longitude": "115.084000",
        },
        follow=False,
    )

    assert response.status_code == 302
    editable_spot.refresh_from_db()
    assert editable_spot.name == "Uluwatu updated"
    assert editable_spot.author == author


@pytest.mark.django_db
def test_author_can_delete_spot(client):
    author = create_user("delete@test.com", "delete")
    deletable_spot = create_spot(author, "Teahupoo", country="PF")

    client.force_login(author)
    response = client.post(reverse("spots:spot_delete", args=[deletable_spot.slug]), follow=False)

    assert response.status_code == 302
    assert not Spot.objects.filter(pk=deletable_spot.pk).exists()


@pytest.mark.django_db
def test_map_data_includes_only_spots_with_coordinates(client):
    author = create_user("map@test.com", "map")
    with_coords = create_spot(author, "Keramas", country="ID", latitude=-8.588, longitude=115.341)
    Spot.objects.create(name="No coords", author=author, country="ID")

    response = client.get(reverse("spots:spot_map_data"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["slug"] == with_coords.slug
