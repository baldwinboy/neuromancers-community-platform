from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from wagtail.coreutils import cautious_slugify

ALL_AUDIENCE = "all"


def audience_choices() -> list[tuple[str, str]]:
    """Audience rules that define a queryset, plus an "All users" option."""
    rules = getattr(settings, "WAGTAIL_DAISIE_AUDIENCE_RULES", {})
    choices: list[tuple[str, str]] = [(ALL_AUDIENCE, _("All users"))]
    for key, rule in rules.items():
        if rule.get("queryset"):
            choices.append((key, rule.get("label", key)))
    return choices


def users_for_audiences(audiences):
    """Return a de-duplicated User queryset for a list of audience keys."""
    from wagtail_daisIE.base_blocks.audience import (  # noqa: PLC0415
        resolve_audience_queryset,
    )

    user_model = get_user_model()
    if ALL_AUDIENCE in audiences:
        return user_model.objects.all()

    query = Q()
    matched = False
    for key in audiences:
        queryset = resolve_audience_queryset(key)
        if queryset is None:
            continue
        matched = True
        # values("pk") keeps the inner query cheap and composable.
        query |= Q(pk__in=queryset.values("pk"))

    if not matched:
        return user_model.objects.none()
    return user_model.objects.filter(query)


def get_reserved_routes():
    reserved_routes = getattr(settings, "WAGTAIL_RESERVED_ROUTES", [])
    if not isinstance(reserved_routes, list):
        reserved_routes = []
    return reserved_routes


def display_reserved_routes_error(slug):
    reserved_routes = get_reserved_routes()
    if not len(reserved_routes):
        return ""
    reserved_routes_list = ", ".join(reserved_routes)
    return _(
        "The slug {slug} is reserved and cannot be used."
        " Please choose a different slug that is not reserved."
        " Reserved slugs: {reserved_routes_list}",
    ).format(
        slug=slug,
        reserved_routes_list=reserved_routes_list,
    )


def is_reserved_route(slug):
    reserved_routes = get_reserved_routes()
    if not len(reserved_routes):
        return False
    return slug in reserved_routes


def prevent_reserved_routes(request, page=None, parent_page=None):
    """
    Prevents pages from being created or edited with reserved routes.
    Redirects back to the appropriate page if the slug is reserved.
    """
    slug = request.POST.get("slug", "").strip().lower()
    slug = cautious_slugify(slug)
    if not is_reserved_route(slug):
        return None

    # Display an error message
    error_message = display_reserved_routes_error(slug)
    if not error_message:
        return None
    messages.error(request, error_message)

    # Determine where to redirect back to
    if not page and not parent_page:
        return redirect("wagtailadmin_home")
    if page:  # editing an existing page
        return redirect("wagtailadmin_pages:edit", args=[page.id])

    # creating a new page
    return redirect("wagtailadmin_pages:add", args=[parent_page.id])
