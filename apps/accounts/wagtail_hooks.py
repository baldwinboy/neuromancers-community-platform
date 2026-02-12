"""
Wagtail hooks and admin interfaces for accounts app.

Registers Certificate and StripeAccount models with wagtail_modeladmin
for clean admin dashboard access.
"""

from guardian.admin import GuardedModelAdmin
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models_users.profile import Certificate, Profile, StripeAccount


class CertificateAdmin(SnippetViewSet, GuardedModelAdmin):
    """Admin interface for issuing and managing Peer certificates."""

    model = Certificate
    icon = "success"
    list_display = ("user", "issued_at", "expires_at")
    list_filter = ("issued_at", "expires_at")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )

    # Allow admins to create/edit certificates easily
    create_template_name = "wagtailadmin/generic/create.html"
    edit_template_name = "wagtailadmin/generic/edit.html"


class StripeAccountAdmin(SnippetViewSet, GuardedModelAdmin):
    """Admin interface for viewing Stripe account connections."""

    model = StripeAccount
    icon = "link"
    list_display = ("user", "is_ready")
    list_filter = ("is_ready",)
    search_fields = ("user__username", "user__email")

    # Stripe accounts are mostly read-only after creation
    read_only_fields = ("id",)


class ProfileAdmin(SnippetViewSet, GuardedModelAdmin):
    """Admin interface for managing user profiles."""

    model = Profile
    icon = "user"
    list_display = ("user", "country")
    search_fields = (
        "user__username",
        "user__email",
        "country",
    )


class AccountsGroup(SnippetViewSetGroup):
    menu_label = "Accounts"
    icon = "user"
    menu_order = 100
    items = (
        CertificateAdmin,
        StripeAccountAdmin,
        ProfileAdmin,
    )


register_snippet(AccountsGroup)
