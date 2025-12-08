from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from django import forms
from django.core.validators import MinValueValidator
from django.db.models import Q
from django.utils.translation import gettext as _

from apps.core.widgets import TypedSelectMultiple
from apps.events.choices import SessionRequestStatusChoices
from apps.events.utils import get_languages

from .mixins import GroupedFormMixin
from .models_sessions.group import GroupSession, GroupSessionRequest
from .models_sessions.peer import (
    PeerSession,
    PeerSessionAvailability,
    PeerSessionRequest,
)

DURATIONS = [[_("Minutes"), list(zip(range(5, 121), range(5, 121)))]]


class PeerSessionForm(GroupedFormMixin, forms.ModelForm):
    host = forms.CharField(required=False)
    price = forms.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
    )
    concessionary_price = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
    )
    per_hour_price = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
        help_text=_(
            "Support seekers will be charged this price based on the duration of their requested session if set"
        ),
    )
    concessionary_per_hour_price = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
        help_text=_(
            "Support seekers will be charged this price based on the duration of their requested session if set"
        ),
    )
    languages = forms.TypedMultipleChoiceField(
        coerce=str,
        choices=get_languages,
        widget=TypedSelectMultiple(
            pattern="^[a-zA-Z ]*$",
            attrs={
                "placeholder": _(
                    "Enter a language, for example, English. Choose a option from the list to add this language."
                ),
                "title": _("Please enter a valid language"),
            },
        ),
        help_text=_("These are languages that a session may be provided in"),
    )
    durations = forms.TypedMultipleChoiceField(
        coerce=int,
        choices=DURATIONS,
        widget=TypedSelectMultiple(
            pattern="^([5-9]|([1-9][0-9])|1[0-1][0-9]|120)$",
            attrs={
                "placeholder": _(
                    "Enter a number, for example, 5 for five minutes. Choose an option from the list to add this duration."
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
            "host",
            "title",
            "description",
            "languages",
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
        (_("Introduction"), ["title", "description", "languages", "durations"]),
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

    def __init__(self, host, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial["host"] = host

        if self.instance and self.instance.pk:
            # Convert price from integer to decimal
            price_decimal = Decimal(self.instance.price) / Decimal(100)
            price_decimal = price_decimal.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            self.initial["price"] = price_decimal

            if self.instance.concessionary_price:
                price_decimal = Decimal(self.instance.concessionary_price) / Decimal(
                    100
                )
                price_decimal = price_decimal.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                self.initial["concessionary_price"] = price_decimal

            if self.instance.per_hour_price:
                price_decimal = Decimal(self.instance.per_hour_price) / Decimal(100)
                price_decimal = price_decimal.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                self.initial["per_hour_price"] = price_decimal

            if self.instance.concessionary_per_hour_price:
                price_decimal = Decimal(
                    self.instance.concessionary_per_hour_price
                ) / Decimal(100)
                price_decimal = price_decimal.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                self.initial["concessionary_per_hour_price"] = price_decimal

            # Convert comma-separated string from model to a list of ints for the form
            durations_str = self.instance.durations
            durations_str = durations_str.strip("[]")
            if durations_str:
                self.initial["durations"] = [int(x) for x in durations_str.split(",")]

            # Convert comma-separated string from model to a list of strings for the form
            languages_str = self.instance.languages
            languages_str = languages_str.strip("[]")
            if languages_str:
                self.initial["languages"] = [
                    lang.strip() for lang in languages_str.split(",") if lang.strip()
                ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        durations_list = self.cleaned_data["durations"]
        languages_list = self.cleaned_data["languages"]
        instance.durations = ",".join(str(d) for d in durations_list)
        instance.languages = ",".join(lang for lang in languages_list)
        if commit:
            instance.save()
        return instance

    def clean_host(self):
        return self.initial["host"]

    def clean_languages(self):
        data = self.cleaned_data.get("languages")
        if not data:
            raise forms.ValidationError(_("You must select at least one language."))
        return data

    def clean_durations(self):
        data = self.cleaned_data.get("durations")
        if not data:
            raise forms.ValidationError(_("You must select at least one duration."))
        return data

    def clean_price(self):
        data = self.cleaned_data["price"]

        if not data:
            return data

        return int(data * 100)

    def clean_concessionary_price(self):
        data = self.cleaned_data["concessionary_price"]

        if not data:
            return data

        return int(data * 100)

    def clean_per_hour_price(self):
        data = self.cleaned_data["per_hour_price"]

        if not data:
            return data

        return int(data * 100)

    def clean_concessionary_per_hour_price(self):
        data = self.cleaned_data["concessionary_per_hour_price"]

        if not data:
            return data

        return int(data * 100)


class GroupSessionForm(GroupedFormMixin, forms.ModelForm):
    host = forms.CharField(required=False)
    language = forms.ChoiceField(
        choices=get_languages,
        help_text=_("This is the language that the session will be provided in"),
    )
    price = forms.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
    )
    concessionary_price = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
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

    class Meta:
        model = GroupSession
        fields = [
            "host",
            "title",
            "description",
            "language",
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
        (_("Introduction"), ["title", "description", "language"]),
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
        super().__init__(*args, **kwargs)

        self.initial["host"] = host

        if self.instance and self.instance.pk:
            # Convert price from integer to decimal
            price_decimal = Decimal(self.instance.price) / Decimal(100)
            price_decimal = price_decimal.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            self.initial["price"] = price_decimal

            if self.instance.concessionary_price:
                price_decimal = Decimal(self.instance.concessionary_price) / Decimal(
                    100
                )
                price_decimal = price_decimal.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                self.initial["concessionary_price"] = price_decimal

    def clean_host(self):
        return self.initial["host"]

    def clean_price(self):
        data = self.cleaned_data["price"]

        if not data:
            return data

        return int(data * 100)

    def clean_concessionary_price(self):
        data = self.cleaned_data["concessionary_price"]

        if not data:
            return data

        return int(data * 100)

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
        help_text=_(
            "This is the start of your availabilty window. All times are set to UTC."
        ),
    )
    ends_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time"}
        ),
        help_text=_(
            "This is the end of your availabilty window. All times are set to UTC."
        ),
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

    def save(self, session: PeerSession, commit=True):
        instance = super().save(commit=False)
        instance.session = session
        if commit:
            instance.save()
        return instance

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


class PeerSessionRequestForm(forms.ModelForm):
    attendee = forms.CharField(required=False)
    session = forms.CharField(required=False)
    starts_at = forms.CharField(widget=forms.HiddenInput())
    ends_at = forms.CharField(widget=forms.HiddenInput())
    language = forms.ChoiceField(
        help_text=_("This is the language that the session will be provided in"),
    )

    class Meta:
        model = PeerSessionRequest
        fields = [
            "attendee",
            "session",
            "language",
            "starts_at",
            "ends_at",
            "pay_concessionary_price",
        ]

    def __init__(self, attendee, session, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial["attendee"] = attendee
        self.initial["session"] = session
        self.fields["language"].choices = session.language_choices

    def clean_starts_at(self):
        data = self.cleaned_data["starts_at"]

        try:
            data = datetime.fromisoformat(data).replace(tzinfo=None)
        except Exception:
            raise forms.ValidationError(
                _("Invalid start time. Try filling out the form again"),
                code="invalid_starts_at",
            )

        return data

    def clean_ends_at(self):
        data = self.cleaned_data["ends_at"]

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

        if self.instance.pk:
            overlapping_requests = overlapping_requests.exclude(pk=self.instance.pk)

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
