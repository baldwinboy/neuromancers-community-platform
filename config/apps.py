"""Project app configs that override third-party (Wagtail) apps.

``wagtail.users`` is not a project app, so the only supported way to swap its
admin viewset (per Wagtail's custom-user docs) is to install an
:class:`~wagtail.users.apps.WagtailUsersAppConfig` subclass in its place. It must
be a separate config class from the project's own app configs.
"""

from __future__ import annotations

from wagtail.users.apps import WagtailUsersAppConfig


class CustomUsersAppConfig(WagtailUsersAppConfig):
    """Use the project's user admin forms (``name``/``date_of_birth``)."""

    user_viewset = "neuromancers_network.users.viewsets.UserViewSet"
