"""Wagtail hooks for the Core app.

Hooks are auto-discovered by Wagtail — no registration needed.
See: https://docs.wagtail.org/en/stable/reference/hooks.html
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from wagtail import hooks

# Slugs that would shadow non-Wagtail routes defined in config/urls.py.
# Because non-Wagtail URLs are matched before Wagtail's catch-all, a page
# created with one of these slugs would never be reachable from the frontend.
RESERVED_SLUGS: frozenset[str] = frozenset(
    [
        # Django admin
        "admin",
        "django-admin",
        # Allauth routes (served at root)
        "login",
        "signup",
        "logout",
        "password",
        "confirm-email",
        "email",
        "reauthenticate",
        # Wagtail admin + media
        "cms",
        "documents",
        # Django user management
        "users",
        # Static / media / API
        "static",
        "media",
        "api",
        # Miscellaneous non-Wagtail views
        "about",
        "health",
        # I18n prefix pattern — Wagtail already handles this, but reserve
        # these so they don't collide if someone removes i18n_patterns
        "en",
        "fr",
        "pt",
        # Common technical slugs
        "robots",
        "sitemap",
        "favicon",
        "__debug__",
    ],
)


def _collect_slugs(page) -> list[str]:
    """Return all slugs in the page's URL path, from root to leaf."""
    slugs: list[str] = [
        ancestor.slug for ancestor in page.get_ancestors(inclusive=False)
    ]
    slugs.append(page.slug)
    return slugs


@hooks.register("before_create_page")
@hooks.register("before_edit_page")
def validate_reserved_slugs(request, page, parent_page=None):
    """Prevent creating or moving a page to a reserved URL path."""
    slugs = _collect_slugs(page)

    # Only check the *top-level* slug — it's the one that would shadow
    # a root-level non-Wagtail route.
    if page.get_parent() and page.get_parent().is_root():
        top_slug = page.slug
    else:
        top_slug = slugs[1] if len(slugs) > 1 else slugs[0]

    if top_slug in RESERVED_SLUGS:
        raise ValidationError(
            _(
                "The slug “%(slug)s” is reserved for a system URL. "
                "Pages at this path would never be reachable. "
                "Please choose a different slug.",
            )
            % {"slug": top_slug},
        )
