"""Admin-authored meeting, booking, refund and review form pages."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey
from wagtail_daisIE.forms.fields import DaisieFormField
from wagtail_daisIE.forms.models import DaisieFormPage

_MEETING_FIELDS = (
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
    "scheduled_at",
    "duration_minutes",
)


def _as_list(value) -> list:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [item.strip() for item in str(value).split(",") if item.strip()]


class MeetingFormField(DaisieFormField):
    page = ParentalKey(
        "meetings.MeetingFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class MeetingFormPage(DaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.meetings.services import (  # noqa: PLC0415
            create_meeting,
        )

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        data = form.cleaned_data
        fields = {key: data[key] for key in _MEETING_FIELDS if key in data}
        fields["tags"] = _as_list(data.get("tags"))
        fields["countries"] = _as_list(data.get("countries"))
        try:
            return create_meeting(peer=user, **fields)
        except PermissionDenied, ValidationError:
            return None


class BookingFormField(DaisieFormField):
    page = ParentalKey(
        "meetings.BookingFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class BookingFormPage(DaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415
        from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415
        from neuromancers_network.meetings.services import (  # noqa: PLC0415
            create_booking,
        )

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        data = form.cleaned_data
        meeting = Meeting.objects.filter(
            pk=data.get("meeting"),
            status=MeetingStatus.PUBLISHED,
        ).first()
        if meeting is None:
            return None

        session = {
            "requested_start_time": data.get("requested_start_time"),
            "requested_duration_minutes": data.get("requested_duration_minutes")
            or meeting.duration_minutes,
        }
        sessions = [session] if session["requested_start_time"] else []
        try:
            return create_booking(
                meeting=meeting,
                seeker=user,
                sessions=sessions,
                access_needs=data.get("access_needs"),
                peer_terms=data.get("peer_terms") or meeting.terms,
                terms_accepted=bool(data.get("agree_to_terms")),
            )
        except PermissionDenied, ValidationError:
            return None


class RefundRequestFormField(DaisieFormField):
    page = ParentalKey(
        "meetings.RefundRequestFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class RefundRequestFormPage(DaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        data = form.cleaned_data
        meeting_request = MeetingRequest.objects.filter(
            pk=data.get("meeting_request"),
            support_seeker=user,
        ).first()
        if meeting_request is None:
            return None
        meeting_request.request_refund(data.get("reason", ""))
        return meeting_request


class ReviewFormField(DaisieFormField):
    page = ParentalKey(
        "meetings.ReviewFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class ReviewFormPage(DaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
        from neuromancers_network.meetings.models import (  # noqa: PLC0415
            MeetingRequestStatus,
        )
        from neuromancers_network.meetings.models import Review  # noqa: PLC0415

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        data = form.cleaned_data
        meeting_request = MeetingRequest.objects.filter(
            pk=data.get("meeting_request"),
            support_seeker=user,
            status=MeetingRequestStatus.COMPLETED,
        ).first()
        if meeting_request is None:
            return None
        return Review.objects.create(
            meeting_request=meeting_request,
            reviewer=user,
            peer=meeting_request.meeting.peer,
            rating=data.get("rating"),
            comment=data.get("comment", ""),
        )
