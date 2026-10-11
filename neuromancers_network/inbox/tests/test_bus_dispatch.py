import pytest
from django.test import RequestFactory

import neuromancers_network.inbox.events as events_module
from neuromancers_network.inbox.actions import notifications_delete
from neuromancers_network.inbox.actions import notifications_mark_all_read
from neuromancers_network.inbox.actions import notifications_mark_read
from neuromancers_network.inbox.events import emit
from neuromancers_network.inbox.models import Notification
from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class _Subscriber:
    def __init__(self, *, is_active=True, event_type="review_created"):
        self.is_active = is_active
        self.event_type = event_type
        self.calls = []
        self.raise_on_call = False

    def handle_event(self, log_entry):
        if self.raise_on_call:
            message = "boom"
            raise RuntimeError(message)
        self.calls.append(log_entry.pk)


class _FakeManager:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, **kwargs):
        return [
            row
            for row in self.rows
            if row.is_active == kwargs["is_active"]
            and row.event_type == kwargs["event_type"]
        ]


class _FakeModel:
    def __init__(self, rows):
        self._default_manager = _FakeManager(rows)


def _register(monkeypatch, subscribers):
    model = _FakeModel(subscribers)
    monkeypatch.setattr(events_module, "get_subscriber_models", lambda: [model])


class TestDispatch:
    def test_active_matching_subscriber_receives_event(self, monkeypatch):
        subscriber = _Subscriber()
        _register(monkeypatch, [subscriber])

        log_entry = emit("review_created")

        assert subscriber.calls == [log_entry.pk]

    def test_inactive_subscriber_is_skipped(self, monkeypatch):
        subscriber = _Subscriber(is_active=False)
        _register(monkeypatch, [subscriber])

        emit("review_created")

        assert subscriber.calls == []

    def test_non_matching_event_type_is_skipped(self, monkeypatch):
        subscriber = _Subscriber(event_type="booking_approved")
        _register(monkeypatch, [subscriber])

        emit("review_created")

        assert subscriber.calls == []

    def test_subscriber_exception_is_swallowed(self, monkeypatch):
        subscriber = _Subscriber()
        subscriber.raise_on_call = True
        _register(monkeypatch, [subscriber])

        # Must not propagate; the log row must still exist.
        log_entry = emit("review_created")

        assert NotificationEventLog.objects.count() == 1
        assert log_entry.pk is not None


def _post(user):
    request = RequestFactory().post("/", {})
    request.user = user
    return request


class TestNotificationPersistence:
    def test_emit_materialises_for_recipients(self):
        user = UserFactory()

        emit("review_created", payload={"recipient_user_ids": [user.pk]})

        assert (
            Notification.objects.filter(
                recipient=user,
                event_type="review_created",
            ).count()
            == 1
        )

    def test_dedupe_by_event_ref(self):
        user = UserFactory()
        payload = {"recipient_user_ids": [user.pk]}

        emit("review_created", payload=payload, event_ref="review:1")
        emit("review_created", payload=payload, event_ref="review:1")

        assert (
            Notification.objects.filter(
                recipient=user,
                event_type="review_created",
            ).count()
            == 1
        )

    def test_without_recipients_no_rows(self):
        emit("review_created", payload={})

        assert Notification.objects.count() == 0


class TestNotificationActions:
    def test_mark_read(self):
        user = UserFactory()
        notification = Notification.objects.create(
            recipient=user,
            event_type="review_created",
        )

        notifications_mark_read(_post(user), {"target": notification.pk})

        notification.refresh_from_db()
        assert notification.is_read is True

    def test_mark_all_read(self):
        user = UserFactory()
        Notification.objects.create(recipient=user, event_type="review_created")
        Notification.objects.create(recipient=user, event_type="review_created")

        notifications_mark_all_read(_post(user), {})

        assert (
            Notification.objects.filter(
                recipient=user,
                read_at__isnull=True,
            ).count()
            == 0
        )

    def test_delete_is_soft(self):
        user = UserFactory()
        notification = Notification.objects.create(
            recipient=user,
            event_type="review_created",
        )

        notifications_delete(_post(user), {"target": notification.pk})

        notification.refresh_from_db()
        assert notification.deleted_at is not None
        assert Notification.objects.filter(pk=notification.pk).exists()
