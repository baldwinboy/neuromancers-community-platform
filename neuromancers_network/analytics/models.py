"""Append-only money, session and activity ledgers.

Every row is keyed by a deterministic ``idempotency_key`` so webhook replays and
backfills converge on the same row. Amounts are stored in major units; a
refund/dispute is recorded as a negative amount.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class TransactionKind(models.TextChoices):
    BOOKING_PAYMENT = "booking_payment", _("Booking payment")
    REFUND = "refund", _("Refund")
    APPLICATION_FEE = "application_fee", _("Application fee")
    DISPUTE = "dispute", _("Dispute")


class SubscriptionKind(models.TextChoices):
    PAYMENT = "subscription_payment", _("Subscription payment")
    REFUND = "subscription_refund", _("Subscription refund")


class TransactionLedger(Timestamped):
    """Marketplace money (payments, fees, refunds, disputes)."""

    kind = models.CharField(
        _("Kind"),
        max_length=32,
        choices=TransactionKind,
        db_index=True,
    )
    base_currency = models.CharField(_("Base currency"), max_length=3)
    base_amount = models.DecimalField(_("Base amount"), max_digits=12, decimal_places=2)
    presentment_currency = models.CharField(_("Presentment currency"), max_length=3)
    presentment_amount = models.DecimalField(
        _("Presentment amount"),
        max_digits=12,
        decimal_places=2,
    )
    exchange_rate = models.DecimalField(
        _("Exchange rate"),
        max_digits=18,
        decimal_places=8,
        null=True,
        blank=True,
    )
    fee_amount = models.DecimalField(
        _("Fee amount"),
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    net_amount = models.DecimalField(_("Net amount"), max_digits=12, decimal_places=2)
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_ledger_paid",
    )
    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_ledger_received",
    )
    provider_object_id = models.CharField(
        _("Provider object ID"),
        max_length=255,
        blank=True,
        db_index=True,
    )
    occurred_at = models.DateTimeField(_("Occurred at"), db_index=True)
    idempotency_key = models.CharField(
        _("Idempotency key"),
        max_length=255,
        unique=True,
    )

    class Meta:
        ordering = ["-occurred_at"]
        verbose_name = _("Transaction ledger entry")
        verbose_name_plural = _("Transaction ledger")
        indexes = [
            models.Index(
                fields=["kind", "occurred_at"],
                name="analytics_txn_kind_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.kind} {self.presentment_amount} {self.presentment_currency}"


class SubscriptionLedger(Timestamped):
    """Recurring platform revenue, kept separate from marketplace money."""

    kind = models.CharField(
        _("Kind"),
        max_length=32,
        choices=SubscriptionKind,
        db_index=True,
    )
    invoice_id = models.CharField(
        _("Invoice ID"),
        max_length=255,
        blank=True,
        db_index=True,
    )
    subscription_id = models.CharField(
        _("Subscription ID"),
        max_length=255,
        blank=True,
        db_index=True,
    )
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_ledger_entries",
    )
    base_currency = models.CharField(_("Base currency"), max_length=3)
    base_amount = models.DecimalField(_("Base amount"), max_digits=12, decimal_places=2)
    presentment_currency = models.CharField(_("Presentment currency"), max_length=3)
    presentment_amount = models.DecimalField(
        _("Presentment amount"),
        max_digits=12,
        decimal_places=2,
    )
    occurred_at = models.DateTimeField(_("Occurred at"), db_index=True)
    idempotency_key = models.CharField(
        _("Idempotency key"),
        max_length=255,
        unique=True,
    )

    class Meta:
        ordering = ["-occurred_at"]
        verbose_name = _("Subscription ledger entry")
        verbose_name_plural = _("Subscription ledger")

    def __str__(self):
        return f"{self.kind} {self.presentment_amount} {self.presentment_currency}"


class SessionLedger(Timestamped):
    """Minutes delivered for a completed session, attributed to a provider."""

    meeting_request = models.OneToOneField(
        "meetings.MeetingRequest",
        on_delete=models.CASCADE,
        related_name="session_ledger",
    )
    provider = models.CharField(_("Provider"), max_length=20, blank=True)
    minutes = models.PositiveIntegerField(_("Minutes"))
    peer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_ledger_as_peer",
    )
    seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_ledger_as_seeker",
    )
    occurred_at = models.DateTimeField(_("Occurred at"), db_index=True)

    class Meta:
        ordering = ["-occurred_at"]
        verbose_name = _("Session ledger entry")
        verbose_name_plural = _("Session ledger")

    def __str__(self):
        return f"{self.minutes} minutes ({self.provider or 'unknown'})"


class ActivityLedger(Timestamped):
    """Temporal facts used for funnel and activity metrics."""

    event_type = models.CharField(_("Event type"), max_length=64, db_index=True)
    object_type = models.CharField(_("Object type"), max_length=64)
    object_id = models.CharField(_("Object ID"), max_length=64)
    occurred_at = models.DateTimeField(_("Occurred at"), db_index=True)
    idempotency_key = models.CharField(
        _("Idempotency key"),
        max_length=255,
        unique=True,
    )

    class Meta:
        ordering = ["-occurred_at"]
        verbose_name = _("Activity ledger entry")
        verbose_name_plural = _("Activity ledger")

    def __str__(self):
        return f"{self.event_type} {self.object_type}:{self.object_id}"
