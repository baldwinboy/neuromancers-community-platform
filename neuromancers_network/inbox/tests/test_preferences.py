import pytest

from neuromancers_network.inbox.forms import NotificationPreferenceAdminForm
from neuromancers_network.inbox.models import NotificationPreference
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestNotificationPreferenceAdminForm:
    def test_initialises_from_stored_list(self):
        pref = NotificationPreference.objects.create(
            user=UserFactory(),
            disabled_event_types=["review_created"],
        )

        form = NotificationPreferenceAdminForm(instance=pref)

        assert form["disabled_event_types"].value() == ["review_created"]

    def test_save_round_trips_list_to_json_and_back(self):
        pref = NotificationPreference.objects.create(user=UserFactory())

        form = NotificationPreferenceAdminForm(
            {
                "user": pref.user_id,
                "disabled_event_types": ["review_created", "booking_paid"],
            },
            instance=pref,
        )
        assert form.is_valid(), form.errors
        form.save()

        pref.refresh_from_db()
        assert set(pref.disabled_event_types) == {"review_created", "booking_paid"}

    def test_unknown_event_type_is_rejected(self):
        pref = NotificationPreference.objects.create(user=UserFactory())

        form = NotificationPreferenceAdminForm(
            {"user": pref.user_id, "disabled_event_types": ["not_an_event"]},
            instance=pref,
        )

        assert not form.is_valid()
        assert "disabled_event_types" in form.errors
