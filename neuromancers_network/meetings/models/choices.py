from django.db import models
from django.utils.translation import gettext_lazy as _


class MeetingType(models.TextChoices):
    ONE_ON_ONE = "1:1", _("1:1")
    GROUP = "group", _("Group")


class PricingType(models.TextChoices):
    PER_HOUR = "per_hour", _("Per hour")
    FIXED = "fixed", _("Fixed price")
    SLIDING_SCALE = "sliding_scale", _("Sliding scale")
    DURATION_TIERS = "duration_tiers", _("Duration tiers")


class ApprovalPolicy(models.TextChoices):
    APPROVAL_REQUIRED = "approval_required", _("Approval required")
    PAY_BEFORE_JOIN = "pay_before_join", _("Pay before join")
    PAY_AFTER_JOIN = "pay_after_join", _("Pay after join")


class MeetingRequestStatus(models.TextChoices):
    PENDING_APPROVAL = "pending_approval", _("Pending approval")
    PENDING_PAYMENT = "pending_payment", _("Pending payment")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    PAID = "paid", _("Paid")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


class RefundStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    REFUNDED = "refunded", _("Refunded")


class MeetingStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class BookingStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PAID = "paid", _("Paid")
    CANCELLED = "cancelled", _("Cancelled")
    REFUNDED = "refunded", _("Refunded")


class RecurrenceFrequency(models.TextChoices):
    DAILY = "daily", _("Daily")
    WEEKLY = "weekly", _("Weekly")
    BIWEEKLY = "biweekly", _("Biweekly")
    MONTHLY = "monthly", _("Monthly")
