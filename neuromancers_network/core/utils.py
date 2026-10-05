from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from wagtail.coreutils import cautious_slugify


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
