"""Admin viewset for user management, using the project's user forms.

Registered in place of Wagtail's default via :class:`config.apps.CustomUsersAppConfig`
(see ``INSTALLED_APPS``), because Wagtail 8 has no ``WAGTAIL_USER_EDIT_FORM`` /
``WAGTAIL_USER_CREATION_FORM`` settings.
"""

from __future__ import annotations

from wagtail.users.views.users import UserViewSet as WagtailUserViewSet

from .forms import UserCreationForm
from .forms import UserEditForm


class UserViewSet(WagtailUserViewSet):
    """Wagtail's user viewset wired to the project's create/edit forms."""

    create_template_name = "users/admin/create.html"
    edit_template_name = "users/admin/edit.html"

    def get_form_class(self, for_update=False):  # noqa: FBT002 - matches Wagtail's signature
        return UserEditForm if for_update else UserCreationForm
