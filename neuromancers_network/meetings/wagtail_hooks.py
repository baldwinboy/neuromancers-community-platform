import json
import logging

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import FieldRowPanel
from wagtail.admin.panels import InlinePanel
from wagtail.admin.panels import MultiFieldPanel
from wagtail.admin.panels import ObjectList
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from neuromancers_network.core.bulk_actions import ConfirmBulkAction
from neuromancers_network.meetings.forms import MeetingAdminForm
from neuromancers_network.meetings.forms import PricingTypeSelect
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
    icon = "calendar-alt"
    menu_label = _("All meetings")
    menu_name = "meetings"
    menu_order = 1
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
    list_per_page = 50
    edit_handler = ObjectList(
        [
            FieldPanel("peer"),
            FieldPanel("title"),
            FieldPanel("description"),
            FieldPanel("terms"),
            FieldPanel("meeting_type"),
            MultiFieldPanel(
                [
                    FieldPanel("scheduled_at"),
                    FieldPanel("duration_minutes"),
                    FieldPanel("max_participants"),
                    FieldPanel("meeting_link"),
                ],
                heading=_("Schedule & capacity"),
                classname="collapsed",
                attrs={
                    "data-w-rules-target": "show",
                    "data-w-rules": json.dumps(
                        {
                            "meeting_type": ["group"],
                        },
                    ),
                },
            ),
            MultiFieldPanel(
                [
                    FieldPanel("pricing_type", widget=PricingTypeSelect),
                    FieldPanel("currency"),
                    InlinePanel(
                        "price_tiers",
                        attrs={
                            "data-w-rules-target": "show",
                            "data-w-rules": json.dumps(
                                {
                                    "pricing_type": ["duration_tiers"],
                                    "meeting_type": ["1:1"],
                                },
                            ),
                            "data-w-rules-match": "all",
                        },
                    ),
                    FieldPanel(
                        "price",
                        attrs={
                            "data-w-rules-target": "show",
                            "data-w-rules": json.dumps(
                                {
                                    "pricing_type": ["fixed", "per_hour"],
                                },
                            ),
                            "data-w-rules-match": "any",
                        },
                    ),
                    FieldRowPanel(
                        [
                            FieldPanel("sliding_scale_min", classname="col6"),
                            FieldPanel("sliding_scale_max", classname="col6"),
                        ],
                        heading=_("Sliding scale"),
                        attrs={
                            "data-w-rules-target": "show",
                            "data-w-rules": json.dumps(
                                {
                                    "pricing_type": ["sliding_scale"],
                                },
                            ),
                        },
                    ),
                ],
                heading=_("Pricing"),
                classname="collapsed",
            ),
            MultiFieldPanel(
                [
                    FieldPanel("approval_policy"),
                    FieldPanel("refund_requires_approval"),
                ],
                heading=_("Approval"),
                classname="collapsed",
            ),
            MultiFieldPanel(
                [
                    FieldRowPanel(
                        [
                            FieldPanel(
                                "languages",
                                classname="w-combobox__menu col6",
                                widget=forms.CheckboxSelectMultiple,
                            ),
                            FieldPanel(
                                "countries",
                                classname="w-combobox__menu col6",
                                widget=forms.CheckboxSelectMultiple,
                            ),
                        ],
                    ),
                    FieldPanel("tags"),
                ],
                heading=_("Filters"),
                classname="collapsed",
            ),
        ],
        base_form_class=MeetingAdminForm,
        attrs={
            "data-controller": "w-rules",
            "data-action": "change->w-rules#resolve",
        },
    )


class BookingViewSet(ModelViewSet):
    model = Booking
    icon = "calendar-check"
    menu_label = _("Bookings")
    menu_name = "bookings"
    menu_order = 2
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
    menu_order = 3
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
    icon = "pick"
    menu_label = _("Reviews")
    menu_name = "reviews"
    menu_order = 4
    list_display = ["peer", "reviewer", "rating", "is_published", "created_at"]
    search_fields = ["comment", "peer__username", "reviewer__username"]
    form_fields = ["rating", "comment", "is_published"]
    list_per_page = 50


class RefundRequestViewSet(ModelViewSet):
    model = RefundRequest
    icon = "rotate"
    menu_label = _("Refund requests")
    menu_name = "refund_requests"
    menu_order = 5
    list_display = ["meeting_request", "status", "created_at"]
    search_fields = ["reason", "meeting_request__meeting__title"]
    form_fields = ["meeting_request", "reason", "peer_response"]
    list_per_page = 50


class MeetingOperationsViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Meetings")
    menu_name = "operations_meetings"
    menu_icon = "calendar"
    menu_order = 2
    items = (
        MeetingViewSet,
        BookingViewSet,
        MeetingPriceTierViewSet,
        ReviewViewSet,
        RefundRequestViewSet,
    )
    add_to_admin_menu = False


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
