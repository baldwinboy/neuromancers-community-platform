from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

from neuromancers_network.core.daisie import DaisyUIAccountAdapterMixin

if TYPE_CHECKING:
    from django.http import HttpRequest


class AccountAdapter(DaisyUIAccountAdapterMixin, DefaultAccountAdapter):
    """Account adapter that renders allauth mail through DaisyUI templates."""

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
