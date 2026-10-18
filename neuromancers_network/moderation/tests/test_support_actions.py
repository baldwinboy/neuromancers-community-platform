import pytest

from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.moderation.models import SupportTicket
from neuromancers_network.moderation.wagtail_hooks import RejectSupportTicketsBulkAction
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestRejectSupportTickets:
    def test_emits_report_rejected_not_resolved(self):
        reporter = UserFactory()
        ticket = SupportTicket.objects.create(reporter=reporter, message="spam")

        RejectSupportTicketsBulkAction.execute_action([ticket], actor=reporter)

        ticket.refresh_from_db()
        assert ticket.status == "rejected"
        assert NotificationEventLog.objects.filter(
            event_type="report_rejected",
            event_ref=f"supportticket.{ticket.pk}.rejected",
        ).exists()
        assert not NotificationEventLog.objects.filter(
            event_type="report_resolved",
            event_ref=f"supportticket.{ticket.pk}.rejected",
        ).exists()
