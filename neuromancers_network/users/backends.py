"""Authentication backends that invalidate deactivated sessions.

``AuthenticationMiddleware`` resolves an existing session through each backend's
``get_user``. ``ModelBackend.get_user`` ignores ``is_active``, and allauth's
backend does not override it, so a member who deactivates would keep a working
session until it expires. These subclasses return ``None`` (yielding
``AnonymousUser``) for deactivated accounts — a central guard that replaces a
dedicated middleware.
"""

from __future__ import annotations

from allauth.account.auth_backends import AuthenticationBackend
from django.contrib.auth.backends import ModelBackend


def _signin_blocked(user) -> bool:
    """Whether an already-authenticated *user* must be signed out."""
    if user is None:
        return False
    if not getattr(user, "is_active", True):
        return True
    return bool(getattr(user, "is_deactivated", False))


class SigninGuardModelBackend(ModelBackend):
    """``ModelBackend`` that refuses to restore a deactivated session."""

    def get_user(self, user_id):
        user = super().get_user(user_id)
        return None if _signin_blocked(user) else user


class SigninGuardAllauthBackend(AuthenticationBackend):
    """allauth backend that refuses to restore a deactivated session."""

    def get_user(self, user_id):
        user = super().get_user(user_id)
        return None if _signin_blocked(user) else user
