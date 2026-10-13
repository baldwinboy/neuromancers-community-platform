import pytest
from django import forms

from neuromancers_network.core.forms import NotificationSettingsForm
from neuromancers_network.core.models import NotificationSettings
from neuromancers_network.inbox.forms import NotificationPreferenceAdminForm
from neuromancers_network.inbox.models import NotificationPreference
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestNotificationPreferenceAdminForm:
    def test_widget_is_checkboxes_not_textarea(self):
        pref = NotificationPreference.objects.create(user=UserFactory())

        form = NotificationPreferenceAdminForm(instance=pref)

        widget = form.fields["disabled_event_types"].widget
        assert isinstance(widget, forms.CheckboxSelectMultiple)

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


class TestNotificationSettingsForm:
    def test_settings_fields_are_checkbox_lists(self):
        form = NotificationSettingsForm(instance=NotificationSettings.load())

        for name in ("default_disabled_event_types", "transactional_events"):
            assert isinstance(
                form.fields[name].widget,
                forms.CheckboxSelectMultiple,
            )
