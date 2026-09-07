from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped
from neuromancers_network.meetings.models.request import MeetingRequest

from .choices import RefundStatus


class RefundRequest(Timestamped):
    meeting_request = models.OneToOneField(
        MeetingRequest,
        on_delete=models.CASCADE,
        related_name="refund_request",
    )
    reason = models.TextField(_("Reason"))
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
    )
    peer_response = models.TextField(_("Peer response"), blank=True)
