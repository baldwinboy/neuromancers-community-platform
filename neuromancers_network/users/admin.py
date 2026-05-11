from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import Profile
from .models import User

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    admin.autodiscover()
    admin.site.login = secure_admin_login(
        admin.site.login)  # type: ignore[method-assign]


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = _("Profile")
    fk_name = "user"
    fields = (
        "bio",
        "languages",
        "country",
        "tier_state",
        "default_tos",
        "default_needs",
        "has_customized",
    )
    readonly_fields = ("tier_state", )


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    inlines = [ProfileInline]
    fieldsets = (
        (None, {
            "fields": ("username", "password")
        }),
        (
            _("Personal info"),
            {
                "fields": ("name", "email", "date_of_birth", "accepted_tos")
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {
            "fields": ("last_login", "date_joined")
        }),
    )
    list_display = ["username", "name", "email", "is_superuser"]
    search_fields = ["name", "username", "email"]
