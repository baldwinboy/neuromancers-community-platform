import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext as _

User = get_user_model()


class AbstractSession(models.Model):
    """
    Sessions are events that may be hosted and managed by `Peer` and `Neuromancer` users and requested and attended by `SupportSeeker` users.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=320)
    description = models.TextField(null=True, blank=True)
    price = models.PositiveSmallIntegerField(default=0)
    concessionary_price = models.PositiveSmallIntegerField(
        help_text=_(
            "Support seekers will be charged at this price if they are allowed to pay a reduced price"
        ),
        null=True,
    )
    access_before_payment = models.BooleanField(
        help_text=_(
            "Support seekers will be able to access the session before payment"
        ),
        default=True,
    )
    require_request_approval = models.BooleanField(
        help_text=_(
            "Support seekers will require peer or admin approval before payment"
        ),
        default=True,
    )
    require_concessionary_approval = models.BooleanField(
        help_text=_(
            "Support seekers will require peer or admin approval to access concessionary price"
        ),
        default=True,
    )
    require_refund_approval = models.BooleanField(
        help_text=_("Support seekers will require approval before payment is refunded"),
        default=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title


class AbstractSessionAvailabilityOccurrenceChoices(models.IntegerChoices):
    """
    Session availability may occur hourly, daily, weekly, monthly, or yearly
    """

    HOURLY = 0, "Hourly"
    DAILY = 1, "Daily"
    WEEKLY = 2, "Weekly"
    MONTHLY = 3, "Monthly"
    YEARLY = 4, "Yearly"


class AbstractSessionAvailability(models.Model):
    """
    Session availability provides windows of time a peer session may be requested or a group session may be attended
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    occurrence = models.PositiveSmallIntegerField(
        choices=AbstractSessionAvailabilityOccurrenceChoices, null=True
    )
    occurrence_starts_at = models.DateTimeField(
        help_text="This is the start of the date range during which the availability occurs. If occurrence is set and this field is not, the specified availbility will occur forever.",
        null=True,
    )
    occurrence_ends_at = models.DateTimeField(
        "This is the start of the date range during which the availability occurs. If occurrence is set and this field is not, the specified availbility will occur from the start date until forever.",
        null=True,
    )

    class Meta:
        abstract = True


class AbstractSessionRequestStatusChoices(models.IntegerChoices):
    """
    Session requests may be approved, rejected, or left pending
    """

    APPROVED = 0, "Approved"
    REJECTED = 1, "Rejected"
    PENDING = 2, "Pending"


class AbstractSessionRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.PositiveSmallIntegerField(
        help_text="By default, this will be pending unless the session does not require approval, then it will be automatically approved. If the request is left pending until the start of the session, the request will be automatically rejected",
        choices=AbstractSessionRequestStatusChoices,
        default=AbstractSessionRequestStatusChoices.PENDING,
    )
    rejection_message = models.TextField(
        help_text="This message will be displayed to the attendee if their request is rejected if set",
        null=True,
    )
    stripe_payment_intent_id = models.CharField(
        help_text="This is set when the user pays for a session",
        null=True,
        max_length=320,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
