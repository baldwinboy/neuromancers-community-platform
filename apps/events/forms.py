from django import forms

from .models_sessions.group import GroupSession
from .models_sessions.peer import PeerSession


class PeerSessionForm(forms.ModelForm):
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


class GroupSessionForm(forms.ModelForm):
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
