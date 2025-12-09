from django import forms
from django.db.models import Q
from django.utils.translation import gettext as _

from apps.events.form_fields import FiltersMultipleChoiceField
from apps.events.mixins import (
    GroupedFormMixin,
    InitialPriceFormMixin,
    PriceFormMixin,
    PublishFormMixin,
)
from apps.events.models_sessions.group import GroupSession, GroupSessionRequest
from apps.events.utils import get_languages

DURATIONS = [[_("Minutes"), list(zip(range(5, 121), range(5, 121)))]]


class GroupSessionForm(
    InitialPriceFormMixin, PriceFormMixin, GroupedFormMixin, forms.ModelForm
):
    host = forms.CharField(required=False)
    language = forms.ChoiceField(
        choices=get_languages,
        help_text=_("This is the language that the session will be provided in"),
    )
    capacity = forms.IntegerField(
        help_text=_("Number of people that can attend at this time"),
        min_value=1,
        max_value=100,
    )
    starts_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
        help_text=_(
            "This is when your scheduled session starts. All times are set to UTC."
        ),
    )
    ends_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
        help_text=_(
            "This is when your scheduled session ends. All times are set to UTC."
        ),
    )
    filters = FiltersMultipleChoiceField()

    class Meta:
        model = GroupSession
        fields = [
            "host",
            "title",
            "description",
            "language",
            "filters",
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
        (
            _("Introduction"),
            [
                "title",
                "description",
                "language",
                "filters",
            ],
        ),
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

    def __init__(self, host, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields["filters"].load_from_request(request)

        self.initial["host"] = host

    def clean_host(self):
        return self.initial["host"]

    def clean(self):
        cleaned_data = super().clean()

        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")
        host = cleaned_data.get("host")

        if not (starts_at and ends_at):
            raise forms.ValidationError(
                _("You must add a start and end time to your session"),
                code="starts_at_and_ends_at",
            )

        if not host:
            raise forms.ValidationError(
                _("A session must be hosted by an existing user"),
                code="required_host",
            )

        overlapping_sessions = GroupSession.objects.filter(
            Q(starts_at__lt=starts_at, ends_at__gt=ends_at)
            | Q(starts_at__gte=starts_at, ends_at__lte=ends_at),
            is_published=True,
            host=host,
        )

        if self.instance.pk:
            overlapping_sessions = overlapping_sessions.exclude(pk=self.instance.pk)

        if overlapping_sessions.exists():
            raise forms.ValidationError(
                _(
                    "Group sessions must not overlap with existing group sessions from the same host"
                ),
                code="overlapping_session",
            )

        return cleaned_data


class GroupSessionPublishForm(PublishFormMixin, forms.ModelForm):
    class Meta:
        model = GroupSession
        fields = ["is_published"]


class GroupSessionRequestForm(forms.ModelForm):
    attendee = forms.CharField(required=False)
    session = forms.CharField(required=False)

    class Meta:
        model = GroupSessionRequest
        fields = ["attendee", "session", "pay_concessionary_price"]

    def __init__(self, attendee, session, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial["attendee"] = attendee
        self.initial["session"] = session

    def clean_session(self):
        return self.initial["session"]

    def clean_attendee(self):
        return self.initial["attendee"]
