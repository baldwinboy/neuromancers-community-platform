"""Consent-cookie write/withdraw endpoints."""

from __future__ import annotations

from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from neuromancers_network.core.consent import ANALYTICS
from neuromancers_network.core.consent import MARKETING
from neuromancers_network.core.consent import clear_consent
from neuromancers_network.core.consent import current_policy_version
from neuromancers_network.core.consent import write_consent


def _return_to(request):
    target = request.POST.get("return_to") or "/"
    if not url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return "/"
    return target


@require_POST
def accept_consent(request):
    """Store the visitor's category choices (accept or necessary-only)."""
    version = (request.POST.get("policy_version") or "").strip()
    if version != current_policy_version():
        return HttpResponseBadRequest(
            "The cookie policy changed; reload the page and try again.",
        )
    choice = request.POST.get("choice") or "accept"
    categories = [] if choice == "necessary" else request.POST.getlist("categories")
    invalid = [value for value in categories if value not in {ANALYTICS, MARKETING}]
    if invalid:
        return HttpResponseBadRequest("Unknown cookie category")

    response = HttpResponseRedirect(_return_to(request))
    write_consent(
        response,
        categories=categories,
        version=version,
        secure=request.is_secure(),
    )
    return response


@require_POST
def reset_consent(request):
    """Withdraw consent and show the banner again on the next page."""
    response = HttpResponseRedirect(_return_to(request))
    clear_consent(response)
    return response
