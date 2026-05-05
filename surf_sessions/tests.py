from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from spots.models import Spot
from surf_sessions.models import Session
from surf_sessions.views import SessionDetailView

User = get_user_model()


def create_user(email, username):
    """Create a CustomUser with the given email, username, and a fixed test password."""
    return User.objects.create_user(
        email=email,
        username=username,
        password="pass1234",
    )


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def user1(db):
    return create_user("u1@test.com", "u1")


@pytest.fixture
def user2(db):
    return create_user("u2@test.com", "u2")


@pytest.fixture
def spot(user1):
    return Spot.objects.create(
        name="Rincon",
        author=user1,
        country="US",
        latitude=35.0,
        longitude=-120.0,
    )


@pytest.fixture
def future_date():
    return timezone.localdate() + timedelta(days=7)


@pytest.fixture
def past_date():
    return timezone.localdate() - timedelta(days=7)


@pytest.fixture
def session(spot, user1, future_date):
    """Default future session with user1 as the organizer and a cap of 5 participants."""
    return Session.objects.create(
        name="Morning session",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="12:00",
        max_participants=5,
    )


@pytest.mark.django_db
def test_session_creation_basic(spot, user1, future_date):
    sess = Session.objects.create(
        name="Sunrise session",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="10:00",
    )
    assert sess.spot == spot
    assert sess.organizer == user1
    assert sess.date == future_date
    assert str(sess).startswith(spot.name)


@pytest.mark.django_db
def test_organizer_is_automatically_participant(spot, user1, future_date):
    sess = Session.objects.create(
        name="Dawn patrol",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="12:00",
    )
    assert user1 in sess.participants.all()
    assert sess.participants_count == 1


@pytest.mark.django_db
def test_participants_count_and_is_full(spot, user1, future_date):
    sess = Session.objects.create(
        name="Afternoon surf",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="12:00",
        max_participants=2,
    )
    assert sess.participants_count == 1
    assert sess.is_full is False

    user_extra = create_user("extra@test.com", "extra")
    sess.participants.add(user_extra)
    sess.refresh_from_db()
    assert sess.participants_count == 2
    assert sess.is_full is True


@pytest.mark.django_db
def test_can_join_unauthenticated_is_false(session):
    class DummyUser:
        is_authenticated = False

    anon = DummyUser()
    assert session.can_join(anon) is False


@pytest.mark.django_db
def test_can_join_user_already_participant_is_false(session, user2):
    session.participants.add(user2)
    assert session.can_join(user2) is False


@pytest.mark.django_db
def test_can_join_normal_user_when_not_full(session, user2):
    assert session.is_full is False
    assert session.can_join(user2) is True


@pytest.mark.django_db
def test_cannot_join_when_full_for_normal_user(spot, user1, user2, future_date):
    sess = Session.objects.create(
        name="Small group",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="12:00",
        max_participants=1,
    )

    assert sess.is_full is True
    assert sess.can_join(user2) is False


@pytest.mark.django_db
def test_organizer_can_join_even_if_full(spot, user1, future_date):
    sess = Session.objects.create(
        name="Organizer slot",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="12:00",
        max_participants=1,
    )
    assert sess.is_full is True
    assert sess.can_join(user1) is True


@pytest.mark.django_db
def test_remove_normal_participant(session, user2):
    session.participants.add(user2)
    assert user2 in session.participants.all()

    session.remove_participant(user2)
    assert user2 not in session.participants.all()


@pytest.mark.django_db
def test_remove_organizer_raises_exception(spot, user1, future_date):
    sess = Session.objects.create(
        name="Protected organizer",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="08:00",
        max_participants=5,
    )

    assert user1 in sess.participants.all()

    with pytest.raises(Exception):
        sess.remove_participant(user1)


@pytest.mark.django_db
def test_session_list_shows_only_future_sessions(client, spot, user1, future_date, past_date):
    future_sess = Session.objects.create(
        name="Future session",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="10:00",
    )
    past_sess = Session.objects.create(
        name="Past session",
        spot=spot,
        organizer=user1,
        date=past_date,
        start_time="10:00",
    )

    client.force_login(user1)
    response = client.get(reverse("surf_sessions:session_list"))

    assert response.status_code == 200
    sessions = list(response.context["sessions"])
    assert future_sess in sessions
    assert past_sess not in sessions


@pytest.mark.django_db
def test_session_detail_context_flags(rf, session, user1, user2):
    view = SessionDetailView.as_view()

    req1 = rf.get(f"/surf_sessions/{session.pk}/")
    req1.user = user1
    resp1 = view(req1, pk=session.pk)
    ctx1 = resp1.context_data

    assert ctx1["is_organizer"] is True
    assert ctx1["already_joined"] is True
    assert ctx1["can_join"] is True

    req2 = rf.get(f"/surf_sessions/{session.pk}/")
    req2.user = user2
    resp2 = view(req2, pk=session.pk)
    ctx2 = resp2.context_data

    assert ctx2["is_organizer"] is False
    assert ctx2["already_joined"] is False
    assert ctx2["can_join"] is True


@pytest.mark.django_db
def test_session_create_sets_organizer_and_spot(client, user1, spot, future_date):
    client.force_login(user1)

    response = client.post(
        reverse("surf_sessions:session_create") + f"?spot={spot.pk}",
        {
            "spot": spot.pk,
            "name": "Afternoon session",
            "date": future_date.isoformat(),
            "start_time": "15:00",
            "end_time": "",
            "max_participants": "",
            "note": "Afternoon session",
        },
        follow=False,
    )

    assert response.status_code == 302

    sess = Session.objects.get(spot=spot, organizer=user1, date=future_date)
    assert sess.note == "Afternoon session"
    assert sess.spot == spot
    assert sess.organizer == user1
    assert user1 in sess.participants.all()


@pytest.mark.django_db
def test_user_can_join_session_via_view(client, session, user2):
    client.force_login(user2)
    response = client.post(reverse("surf_sessions:session_join", args=[session.pk]), follow=False)

    assert response.status_code == 302
    session.refresh_from_db()
    assert user2 in session.participants.all()


@pytest.mark.django_db
def test_user_cannot_join_twice_via_view(client, session, user2):
    client.force_login(user2)
    url = reverse("surf_sessions:session_join", args=[session.pk])
    client.post(url)
    session.refresh_from_db()
    assert user2 in session.participants.all()

    count_before = session.participants_count
    client.post(url)
    session.refresh_from_db()
    assert session.participants_count == count_before


@pytest.mark.django_db
def test_user_can_leave_session_via_view(client, session, user2):
    session.participants.add(user2)
    session.refresh_from_db()
    assert user2 in session.participants.all()

    client.force_login(user2)
    response = client.post(reverse("surf_sessions:session_leave", args=[session.pk]), follow=False)

    assert response.status_code == 302
    session.refresh_from_db()
    assert user2 not in session.participants.all()


@pytest.mark.django_db
def test_organizer_cannot_leave_via_view(client, session, user1):
    client.force_login(user1)
    response = client.post(reverse("surf_sessions:session_leave", args=[session.pk]), follow=False)

    assert response.status_code == 302
    session.refresh_from_db()
    assert user1 in session.participants.all()


@pytest.mark.django_db
def test_join_fails_when_full_via_view(client, spot, user1, user2, future_date):
    sess = Session.objects.create(
        name="Packed session",
        spot=spot,
        organizer=user1,
        date=future_date,
        start_time="10:00",
        max_participants=1,
    )
    assert sess.is_full is True

    client.force_login(user2)
    response = client.post(reverse("surf_sessions:session_join", args=[sess.pk]), follow=False)

    assert response.status_code == 302
    sess.refresh_from_db()
    assert user2 not in sess.participants.all()


@pytest.mark.django_db
def test_only_organizer_can_access_update_view(client, session, user1, user2):
    client.force_login(user2)
    response = client.get(reverse("surf_sessions:session_update", args=[session.pk]), follow=False)

    assert response.status_code == 302
    assert reverse("surf_sessions:session_detail", args=[session.pk]) in response.headers["Location"]


@pytest.mark.django_db
def test_organizer_can_update_session_data(client, session, user1, spot):
    client.force_login(user1)
    new_note = "Updated note"

    if isinstance(session.start_time, str):
        start_value = session.start_time
    else:
        start_value = session.start_time.strftime("%H:%M")

    response = client.post(
        reverse("surf_sessions:session_update", args=[session.pk]),
        {
            "spot": spot.pk,
            "name": session.name,
            "date": session.date.isoformat(),
            "start_time": start_value,
            "end_time": "",
            "max_participants": session.max_participants or "",
            "note": new_note,
        },
        follow=False,
    )

    assert response.status_code == 302
    session.refresh_from_db()
    assert session.note == new_note


@pytest.mark.django_db
def test_session_create_without_query_param_uses_selected_spot(client, user1, spot, future_date):
    client.force_login(user1)

    response = client.post(
        reverse("surf_sessions:session_create"),
        {
            "spot": spot.pk,
            "name": "Open create flow",
            "date": future_date.isoformat(),
            "start_time": "16:00",
            "end_time": "",
            "max_participants": "",
            "note": "",
        },
        follow=False,
    )

    assert response.status_code == 302
    assert Session.objects.filter(
        spot=spot,
        organizer=user1,
        name="Open create flow",
    ).exists()


@pytest.mark.django_db
def test_only_organizer_can_delete_session(client, session, user1, user2):
    client.force_login(user2)
    response = client.post(reverse("surf_sessions:session_delete", args=[session.pk]), follow=False)
    assert response.status_code == 302
    assert Session.objects.filter(pk=session.pk).exists()

    client.force_login(user1)
    response = client.post(reverse("surf_sessions:session_delete", args=[session.pk]), follow=False)
    assert response.status_code == 302
    assert not Session.objects.filter(pk=session.pk).exists()
