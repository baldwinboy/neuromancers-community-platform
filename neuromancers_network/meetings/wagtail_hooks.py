import logging

from django.forms import modelform_factory
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import InlinePanel
from wagtail.admin.viewsets.model import ModelViewSet

from neuromancers_network.core.bulk_actions import ConfirmBulkAction
from neuromancers_network.meetings.forms import MeetingAdminForm
from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import RefundRequest
from neuromancers_network.meetings.models import RefundStatus
from neuromancers_network.meetings.models import Review

logger = logging.getLogger(__name__)


class MeetingFilterSet(WagtailFilterSet):
    class Meta:
        model = Meeting
        fields = [
            "status",
            "meeting_type",
            "pricing_type",
            "approval_policy",
            "countries",
            "languages",
        ]


class MeetingViewSet(ModelViewSet):
    model = Meeting
    icon = "date"
    menu_label = _("Meetings")
    menu_name = "meetings"
    menu_order = 4
    list_display = [
        "title",
        "peer",
        "status",
        "meeting_type",
        "pricing_type",
        "scheduled_at",
    ]
    search_fields = ["title", "description", "peer__username", "peer__name"]
    filterset_class = MeetingFilterSet
    form_fields = [
        "peer",
        "title",
        "description",
        "terms",
        "meeting_type",
        "meeting_link",
        "pricing_type",
        "price",
        "sliding_scale_min",
        "sliding_scale_max",
        "currency",
        "approval_policy",
        "refund_requires_approval",
        "max_participants",
        "languages",
        "countries",
        "tags",
        "scheduled_at",
        "duration_minutes",
    ]
    list_per_page = 50

    def get_form_class(self, for_update=False):  # noqa: FBT002
        return modelform_factory(
            self.model,
            form=MeetingAdminForm,
            fields=self.get_form_fields(),
        )


class RefundRequestViewSet(ModelViewSet):
    model = RefundRequest
    icon = "undo"
    menu_label = _("Refund requests")
    menu_name = "refund_requests"
    menu_order = 5
    list_display = ["meeting_request", "status", "created_at"]
    search_fields = ["reason", "meeting_request__meeting__title"]
    form_fields = ["meeting_request", "reason", "peer_response"]
    list_per_page = 50


class BookingViewSet(ModelViewSet):
    model = Booking
    icon = "tick-inverse"
    menu_label = _("Bookings")
    menu_name = "bookings"
    menu_order = 7
    list_display = [
        "meeting",
        "support_seeker",
        "status",
        "total_amount",
        "created_at",
    ]
    search_fields = [
        "meeting__title",
        "support_seeker__username",
        "support_seeker__name",
    ]
    form_fields = [
        "meeting",
        "support_seeker",
        "total_amount",
        "currency",
        "stripe_checkout_session_id",
        "stripe_payment_intent_id",
        "access_needs",
    ]
    list_per_page = 50


class MeetingPriceTierViewSet(ModelViewSet):
    model = MeetingPriceTier
    icon = "tag"
    menu_label = _("Price tiers")
    menu_name = "price_tiers"
    menu_order = 8
    list_display = ["meeting", "duration_minutes", "is_default"]
    search_fields = ["meeting__title"]
    panels = [
        FieldPanel("meeting"),
        FieldPanel("duration_minutes"),
        FieldPanel("is_default"),
        InlinePanel("options"),
    ]
    list_per_page = 50


class ReviewViewSet(ModelViewSet):
    model = Review
    icon = "star"
    menu_label = _("Reviews")
    menu_name = "reviews"
    menu_order = 6
    list_display = ["peer", "reviewer", "rating", "is_published", "created_at"]
    search_fields = ["comment", "peer__username", "reviewer__username"]
    form_fields = ["rating", "comment", "is_published"]
    list_per_page = 50


class PublishMeetingBulkAction(ConfirmBulkAction):
    models = [Meeting]
    display_name = _("Publish")
    action_type = "publish"
    aria_label = _("Publish selected meetings")
    icon = "upload"
    confirm_message = _("Publish the selected meetings?")
    action_button_text = _("Yes, publish")
    no_action_button_text = _("No, go back")

    @classmethod
    def execute_action(cls, objects, **kwargs):
        published = 0
        for meeting in objects:
            if meeting.status == MeetingStatus.DRAFT:
                meeting.publish()
                meeting.save(validate=False, update_fields=["status", "updated_at"])
                published += 1
        return published, 0


class UnpublishMeetingBulkAction(ConfirmBulkAction):
    models = [Meeting]
    display_name = _("Unpublish")
    action_type = "unpublish"
    aria_label = _("Unpublish selected meetings")
    icon = "download"
    confirm_message = _("Unpublish the selected meetings?")
    action_button_text = _("Yes, unpublish")
    no_action_button_text = _("No, go back")

    @classmethod
    def execute_action(cls, objects, **kwargs):
        unpublished = 0
        for meeting in objects:
            if meeting.status == MeetingStatus.PUBLISHED:
                meeting.unpublish()
                meeting.save(validate=False, update_fields=["status", "updated_at"])
                unpublished += 1
        return unpublished, 0


class ArchiveMeetingBulkAction(ConfirmBulkAction):
    models = [Meeting]
    display_name = _("Archive")
    action_type = "archive"
    aria_label = _("Archive selected meetings")
    icon = "folder-open-inverse"
    confirm_message = _("Archive the selected meetings?")
    action_button_text = _("Yes, archive")
    no_action_button_text = _("No, go back")

    @classmethod
    def execute_action(cls, objects, **kwargs):
        archived = 0
        for meeting in objects:
            if meeting.status in {MeetingStatus.DRAFT, MeetingStatus.PUBLISHED}:
                meeting.archive()
                meeting.save(validate=False, update_fields=["status", "updated_at"])
                archived += 1
        return archived, 0


class ApproveRefundBulkAction(ConfirmBulkAction):
    models = [RefundRequest]
    display_name = _("Approve refund")
    action_type = "approve"
    aria_label = _("Approve selected refund requests")
    icon = "check"
    confirm_message = _("Approve the selected refunds? This issues Stripe refunds.")
    action_button_text = _("Yes, approve")
    no_action_button_text = _("No, go back")

    @classmethod
    def execute_action(cls, objects, **kwargs):
        approved = 0
        for refund in objects:
            if refund.status == RefundStatus.PENDING:
                try:
                    refund.approve()
                except Exception:
                    logger.exception("Failed to approve refund request %s", refund.pk)
                    continue
                refund.save()
                approved += 1
        return approved, 0


class RejectRefundBulkAction(ConfirmBulkAction):
    models = [RefundRequest]
    display_name = _("Reject refund")
    action_type = "reject"
    aria_label = _("Reject selected refund requests")
    icon = "no"
    confirm_message = _("Reject the selected refunds?")
    action_button_text = _("Yes, reject")
    no_action_button_text = _("No, go back")

    @classmethod
    def execute_action(cls, objects, **kwargs):
        rejected = 0
        for refund in objects:
            if refund.status == RefundStatus.PENDING:
                refund.reject()
                refund.save()
                rejected += 1
        return rejected, 0


class PublishReviewBulkAction(ConfirmBulkAction):
    models = [Review]
    display_name = _("Publish")
    action_type = "publish"
    aria_label = _("Publish selected reviews")
    icon = "upload"
    confirm_message = _("Publish the selected reviews?")
    action_button_text = _("Yes, publish")
    no_action_button_text = _("No, go back")

    @classmethod
    def execute_action(cls, objects, **kwargs):
        published = 0
        for review in objects:
            if not review.is_published:
                review.is_published = True
                review.save(update_fields=["is_published", "updated_at"])
                published += 1
        return published, 0


class UnpublishReviewBulkAction(ConfirmBulkAction):
    models = [Review]
    display_name = _("Unpublish")
    action_type = "unpublish"
    aria_label = _("Unpublish selected reviews")
    icon = "download"
    confirm_message = _("Unpublish the selected reviews?")
    action_button_text = _("Yes, unpublish")
    no_action_button_text = _("No, go back")

    @classmethod
    def execute_action(cls, objects, **kwargs):
        unpublished = 0
        for review in objects:
            if review.is_published:
                review.is_published = False
                review.save(update_fields=["is_published", "updated_at"])
                unpublished += 1
        return unpublished, 0


for action_class in [
    PublishMeetingBulkAction,
    UnpublishMeetingBulkAction,
    ArchiveMeetingBulkAction,
    ApproveRefundBulkAction,
    RejectRefundBulkAction,
    PublishReviewBulkAction,
    UnpublishReviewBulkAction,
]:
    hooks.register("register_bulk_action", action_class)
