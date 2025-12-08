import uuid

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext as _

from apps.events.choices import (
    SessionAvailabilityOccurrenceChoices,
    SessionRequestStatusChoices,
    currency_choices,
)

User = get_user_model()


class AbstractSession(models.Model):
    """
    Sessions are events that may be hosted and managed by `Peer` and `Neuromancer` users and requested and attended by `SupportSeeker` users.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=320)
    description = models.TextField(null=True, blank=True)
    currency = models.CharField(max_length=3, choices=currency_choices, default="GBP")
    price = models.IntegerField(
        default=0,
        validators=[
            MinValueValidator(0, message=_("Cannot charge negative values")),
            MaxValueValidator(
                9_999_999,
                message=_(
                    "Cannot charge over 99,999 of a currency's unit. For higher values, try a different currency."
                ),
            ),
        ],
    )
    concessionary_price = models.IntegerField(
        validators=[
            MinValueValidator(0, message=_("Cannot charge negative values")),
            MaxValueValidator(
                9_999_999,
                message=_(
                    "Cannot charge over 99,999 of a currency's unit. For higher values, try a different currency."
                ),
            ),
        ],
        help_text=_(
            "Support seekers will be charged at this price if they are allowed to pay a reduced price"
        ),
        null=True,
        blank=True,
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
    filters = models.JSONField(
        help_text=_("These are filters applied for a session"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    @property
    def price_display(self):
        return "{:.2f}".format(self.price / 100)

    @property
    def concessionary_price_display(self):
        if not self.concessionary_price:
            return "{:.2f}".format(0)

        return "{:.2f}".format(self.concessionary_price / 100)


class AbstractSessionAvailability(models.Model):
    """
    Session availability provides windows of time a peer session may be requested or a group session may be attended
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    occurrence = models.PositiveSmallIntegerField(
        choices=SessionAvailabilityOccurrenceChoices, null=True, blank=True
    )
    occurrence_starts_at = models.DateTimeField(
        help_text=_(
            "This is the start of the date range during which the availability occurs. If occurrence is set and this field is not, the specified availbility will occur forever."
        ),
        null=True,
    )
    occurrence_ends_at = models.DateTimeField(
        help_text=_(
            "This is the start of the date range during which the availability occurs. If occurrence is set and this field is not, the specified availbility will occur from the start date until forever."
        ),
        null=True,
        verbose_name=_("Occurrence ends at"),
    )

    class Meta:
        abstract = True


class AbstractSessionRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.PositiveSmallIntegerField(
        help_text=_(
            "By default, this will be pending unless the session does not require approval, then it will be automatically approved. If the request is left pending until the start of the session, the request will be automatically rejected"
        ),
        choices=SessionRequestStatusChoices,
        default=SessionRequestStatusChoices.PENDING,
    )
    rejection_message = models.TextField(
        help_text=_(
            "This message will be displayed to the attendee if their request is rejected if set"
        ),
        null=True,
    )
    stripe_payment_intent_id = models.CharField(
        help_text=_("This is set when the user pays for a session"),
        null=True,
        max_length=320,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pay_concessionary_price = models.BooleanField(
        help_text=_(
            "You'll be able to pay a reduced price if the session peer approves."
        ),
        default=False,
    )
    concessionary_status = models.PositiveSmallIntegerField(
        help_text=_(
            "By default, this will be pending unless concessionary price request do not require approval, then it will be automatically approved. If the request is left pending until the start of the session, the request will be automatically rejected"
        ),
        choices=SessionRequestStatusChoices,
        default=SessionRequestStatusChoices.PENDING,
    )
    refund_status = models.PositiveSmallIntegerField(
        help_text=_(
            "By default, this will be pending unless refunds does not require approval, then it will be automatically approved. If the request is left pending until the start of the session, the request will be automatically rejected"
        ),
        choices=SessionRequestStatusChoices,
        default=SessionRequestStatusChoices.PENDING,
    )
    refunded = models.BooleanField(
        help_text=_(
            """
                Payments will refunded if:
                    (a) refunds are automatically approved and a user withdraws an approved request
                    (b) a user requests a refund and the request is approved
            """
        ),
        default=True,
    )

    class Meta:
        abstract = True


class AbstractSessionReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    content = models.TextField()

    class Meta:
        abstract = True
