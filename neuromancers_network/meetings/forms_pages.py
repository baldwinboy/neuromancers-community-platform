# ruff: noqa: PLC0415
"""Admin-authored meeting, booking, refund and review form pages."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey
from wagtail_daisIE.forms.fields import DaisieFormField

from neuromancers_network.core.forms_pages import ProjectDaisieFormPage
from neuromancers_network.meetings.constants import MEETING_FORM_FIELDS


def _as_list(value) -> list:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _tier_rows(page, data):
    """Return the cleaned duration-tier rows from *data*, if present."""
    for field in page.get_form_fields():
        if getattr(field, "field_type", "") == "duration_tiers":
            return data.get(field.clean_name)
    return None


class MeetingFormField(DaisieFormField):
    page = ParentalKey(
        "meetings.MeetingFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class MeetingFormPage(ProjectDaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.meetings.services import apply_duration_tiers
        from neuromancers_network.meetings.services import create_meeting

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        data = form.cleaned_data
        fields = {key: data[key] for key in MEETING_FORM_FIELDS if key in data}
        fields["tags"] = _as_list(data.get("tags"))
        fields["countries"] = _as_list(data.get("countries"))
        fields["languages"] = _as_list(data.get("languages"))
        try:
            meeting = create_meeting(peer=user, **fields)
        except PermissionDenied, ValidationError:
            return None

        rows = _tier_rows(self, data)
        if rows:
            apply_duration_tiers(meeting, rows)
        return meeting


class MeetingEditFormField(DaisieFormField):
    page = ParentalKey(
        "meetings.MeetingEditFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class MeetingEditFormPage(ProjectDaisieFormPage):
    """Host-facing edit page for an existing 1:1 or group meeting."""

    template = "wagtail_daisIE/forms/form_page.html"
    form_mode = "edit"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    def update_instance_from_submission(self, form, instance, submission=None):
        from neuromancers_network.meetings.services import apply_duration_tiers

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if instance is None or user is None or not user.is_authenticated:
            return None
        if instance.peer_id != user.pk and not getattr(user, "is_moderator", False):
            return None

        result = super().update_instance_from_submission(
            form,
            instance,
            submission=submission,
        )
        if result is not None:
            rows = _tier_rows(self, form.cleaned_data)
            if rows:
                apply_duration_tiers(result, rows)
        return result


class BookingFormField(DaisieFormField):
    page = ParentalKey(
        "meetings.BookingFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class BookingFormPage(ProjectDaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.meetings.models import Meeting
        from neuromancers_network.meetings.models import MeetingStatus
        from neuromancers_network.meetings.services import create_booking

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


class RefundRequestFormPage(ProjectDaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.meetings.models import MeetingRequest

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
        meeting_request.request_refund(
            data.get("reason", ""),
            amount=data.get("amount") or None,
        )
        return meeting_request


class ReviewFormField(DaisieFormField):
    page = ParentalKey(
        "meetings.ReviewFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class ReviewFormPage(ProjectDaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.meetings.models import MeetingRequest
        from neuromancers_network.meetings.models import MeetingRequestStatus
        from neuromancers_network.meetings.models import Review
        from neuromancers_network.meetings.models import ReviewStatus

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
        peer_profile = getattr(meeting_request.meeting.peer, "peer_profile", None)
        if peer_profile is not None and not peer_profile.accepts_reviews:
            return None
        status = (
            ReviewStatus.PENDING_APPROVAL
            if peer_profile is not None and peer_profile.reviews_require_approval
            else ReviewStatus.PUBLISHED
        )
        return Review.objects.create(
            meeting_request=meeting_request,
            reviewer=user,
            peer=meeting_request.meeting.peer,
            rating=data.get("rating"),
            comment=data.get("comment", ""),
            status=status,
        )
