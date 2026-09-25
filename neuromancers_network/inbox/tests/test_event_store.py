import pytest

from neuromancers_network.inbox.events import emit
from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.inbox.models import NotificationEventType

pytestmark = pytest.mark.django_db


class TestEmit:
    def test_records_event_log_row(self):
        log_entry = emit(
            NotificationEventType.REVIEW_CREATED,
            payload={"meta": {"rating": 5}},
            event_ref="review.1.created",
        )

        assert NotificationEventLog.objects.count() == 1
        log_entry.refresh_from_db()
        assert log_entry.event_type == NotificationEventType.REVIEW_CREATED
        assert log_entry.event_ref == "review.1.created"
        assert log_entry.payload == {"meta": {"rating": 5}}
        assert log_entry.status == "recorded"

    def test_accepts_string_value(self):
        emit("review_created", event_ref="review.2.created")
        assert NotificationEventLog.objects.get().event_type == "review_created"

    def test_rejects_unknown_event_type(self):
        with pytest.raises(ValueError, match="Unknown event type"):
            emit("not.a.real.event")  # type: ignore[arg-type]
