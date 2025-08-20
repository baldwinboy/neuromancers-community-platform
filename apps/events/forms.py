from datetime import datetime
from django import forms
from django.db.models import Q
from django.utils.translation import gettext as _

from apps.core.widgets import TypedSelectMultiple
from apps.events.choices import SessionRequestStatusChoices

from .mixins import GroupedFormMixin
from .models_sessions.group import GroupSession
from .models_sessions.peer import (
    PeerSession,
    PeerSessionAvailability,
    PeerSessionRequest,
)

DURATIONS = [[_("Minutes"), list(zip(range(5, 121), range(5, 121)))]]

class PeerSessionForm(GroupedFormMixin, forms.ModelForm):
    durations = forms.TypedMultipleChoiceField(
        coerce=int,
        choices=DURATIONS,
        widget=TypedSelectMultiple(
            pattern="^([5-9]|([1-9][0-9])|1[0-1][0-9]|120)$",
            attrs={
                "placeholder": _(
                    "Enter a number, for example, 5 for five minutes. Choose a option from the list to add this duration."
                ),
                "title": _("Please enter a valid number between 5 and 120"),
            },
        ),
        help_text=_(
            "These are durations (in minutes) that a session may be booked for"
        ),
    )

    class Meta:
        model = PeerSession
        fields = [
            "title",
            "description",
            "durations",
            "currency",
            "price",
            "concessionary_price",
            "access_before_payment",
            "require_request_approval",
            "require_concessionary_approval",
            "require_refund_approval",
            "per_hour_price",
            "concessionary_per_hour_price",
        ]

    field_groups = [
        (_("Introduction"), ["title", "description", "durations"]),
        (_("Pricing"), ["currency", "price", "per_hour_price"]),
        (
            _("Concessionary Pricing"),
            ["concessionary_price", "concessionary_per_hour_price"],
        ),
        (
            _("Access Settings"),
            [
                "access_before_payment",
                "require_request_approval",
                "require_concessionary_approval",
                "require_refund_approval",
            ],
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Convert comma-separated string from model to a list of ints for the form
        if self.instance and self.instance.pk:
            durations_str = self.instance.durations
            if durations_str:
                self.initial["durations"] = [int(x) for x in durations_str.split(",")]

    def save(self, commit=True):
        instance = super().save(commit=False)
        durations_list = self.cleaned_data["durations"]
        instance.durations = ",".join(str(d) for d in durations_list)
        if commit:
            instance.save()
        return instance


class GroupSessionForm(GroupedFormMixin, forms.ModelForm):
    capacity = forms.IntegerField(
        help_text=_("Number of people that can attend at this time"),
        min_value=1,
        max_value=100,
    )
    starts_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
        help_text=_("This is when your scheduled session starts. All times are set to UTC.")
    )
    ends_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
        help_text=_("This is when your scheduled session ends. All times are set to UTC.")
    )

    class Meta:
        model = GroupSession
        fields = [
            "title",
            "description",
            "currency",
            "price",
            "concessionary_price",
            "access_before_payment",
            "require_request_approval",
            "require_concessionary_approval",
            "require_refund_approval",
            "starts_at",
            "ends_at",
            "capacity",
            "meeting_link",
        ]

    field_groups = [
        (_("Introduction"), ["title", "description"]),
        (_("Schedule"), ["starts_at", "ends_at", "meeting_link"]),
        (_("Pricing"), ["currency", "price"]),
        (
            _("Concessionary Pricing"),
            ["concessionary_price"],
        ),
        (
            _("Access Settings"),
            [
                "capacity",
                "access_before_payment",
                "require_request_approval",
                "require_concessionary_approval",
                "require_refund_approval",
            ],
        ),
    ]

    def clean(self):
        cleaned_data = super().clean()

        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")

        if not (starts_at and ends_at):
            raise forms.ValidationError(
                _("You must add a start and end time to your session"),
                code="starts_at_and_ends_at",
            )

        return cleaned_data


class PeerSessionPublishForm(forms.ModelForm):
    class Meta:
        model = PeerSession
        fields = ["is_published"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_published = not instance.is_published
        if commit:
            instance.save()
        return instance


class GroupSessionPublishForm(forms.ModelForm):
    class Meta:
        model = GroupSession
        fields = ["is_published"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_published = not instance.is_published
        if commit:
            instance.save()
        return instance


class PeerSessionAvailabilityForm(forms.ModelForm):
    starts_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
        help_text=_("This is the start of your availabilty window. All times are set to UTC.")
    )
    ends_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
        help_text=_("This is the end of your availabilty window. All times are set to UTC.")
    )
    occurrence_starts_at = forms.SplitDateTimeField(
        required=False,
        help_text=_(
            "This is the start of the date range during which the availability occurs. If occurrence is set and this field is not, the specified availbility will occur forever. All times are set to UTC."
        ),
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
    )
    occurrence_ends_at = forms.SplitDateTimeField(
        required=False,
        help_text=_(
            "This is the end of the date range during which the availability occurs. If occurrence is set and this field is not, the specified availbility will occur forever. All times are set to UTC."
        ),
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
    )

    class Meta:
        model = PeerSessionAvailability
        fields = [
            "starts_at",
            "ends_at",
            "occurrence",
            "occurrence_starts_at",
            "occurrence_ends_at",
        ]

    def clean(self):
        cleaned_data = super().clean()

        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")

        if not (starts_at and ends_at):
            raise forms.ValidationError(
                _("You must add a start and end time to your availaibilty"),
                code="starts_at_and_ends_at",
            )

        return cleaned_data

    def save(self, session: PeerSession, commit=True):
        instance = super().save(commit=False)
        instance.session = session
        if commit:
            instance.save()
        return instance


class PeerSessionRequestForm(forms.ModelForm):
    attendee = forms.CharField(required=False)
    session = forms.CharField(required=False)
    starts_at = forms.CharField(widget=forms.HiddenInput())
    ends_at = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = PeerSessionRequest
        fields = ["attendee", "session", "starts_at", "ends_at", "pay_concessionary_price"]

    def __init__(self, attendee, session, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial["attendee"] = attendee
        self.initial["session"] = session
        
    def clean_starts_at(self):
        data = self.cleaned_data['starts_at']

        try:
            data = datetime.fromisoformat(data).replace(tzinfo=None)
        except Exception:
            raise forms.ValidationError(
                _("Invalid start time. Try filling out the form again"),
                code="invalid_starts_at",
            )
        
        return data
    
    def clean_ends_at(self):
        data = self.cleaned_data['ends_at']

        try:
            data = datetime.fromisoformat(data).replace(tzinfo=None)
        except Exception:
            raise forms.ValidationError(
                _("Invalid end time. Try filling out the form again"),
                code="invalid_ends_at",
            )
        
        return data
    
    def clean_session(self):
        return self.initial["session"]
    
    def clean_attendee(self):
        return self.initial["attendee"]
    
    def clean(self):
        cleaned_data = super().clean()

        attendee = cleaned_data.get("attendee")
        session = cleaned_data.get("session")
        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")

        if not (starts_at and ends_at):
            raise forms.ValidationError(
                _("You must add a start and end time to your request"),
                code="starts_at_and_ends_at",
            )
        
        # Session requests should not overlap with existing approved session requests from the same attendee
        overlapping_requests = PeerSessionRequest.objects.filter(
            Q(starts_at__lt=starts_at, ends_at__gt=ends_at)
            | Q(starts_at__gte=starts_at, ends_at__lte=ends_at),
            attendee=attendee,
            session=session,
            status=SessionRequestStatusChoices.APPROVED,
        )

        if overlapping_requests.exists():
            raise forms.ValidationError(
                _(
                    "Session requests should not conflict with existing session requests from the same support seeker"
                ),
                code="overlapping_requests",
            )

        for k in cleaned_data.keys():
            if k not in self.fields:
                cleaned_data.pop(k, None)

        return cleaned_data