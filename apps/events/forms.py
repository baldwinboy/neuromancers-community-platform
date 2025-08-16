from django import forms
from django.utils.translation import gettext as _

from .mixins import GroupedFormMixin
from .models_sessions.group import GroupSession
from .models_sessions.peer import PeerSession


class PeerSessionForm(GroupedFormMixin, forms.ModelForm):
    class Meta:
        model = PeerSession
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
            "per_hour_price",
            "concessionary_per_hour_price",
        ]

    field_groups = [
        (_("Introduction"), ["title", "description"]),
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


class GroupSessionForm(GroupedFormMixin, forms.ModelForm):
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
        widgets = {
            "starts_at": forms.SplitDateTimeWidget(
                date_attrs={"type": "date"}, time_attrs={"type": "time"}
            ),
            "ends_at": forms.SplitDateTimeWidget(
                date_attrs={"type": "date"}, time_attrs={"type": "time"}
            ),
        }

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
