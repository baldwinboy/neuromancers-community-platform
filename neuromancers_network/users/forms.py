import logging

from allauth.account.forms import AddEmailForm as BaseAddEmailForm
from allauth.account.forms import SignupForm
from django import forms
from django.utils.translation import gettext_lazy as _

from neuromancers_network.moderation.identity import is_identity_blocked
from neuromancers_network.users.cooldown import ensure_email_change_allowed
from neuromancers_network.users.validators import validate_username_not_blocked

logger = logging.getLogger(__name__)


class UserSignupForm(SignupForm):
    """
    Form rendered on the user sign up screen.

    Default fields are added automatically from ``ACCOUNT_SIGNUP_FIELDS``.
    """

    accept_tos = forms.BooleanField(
        label=_("I accept the Terms and Conditions"),
        required=True,
    )

    def clean_username(self) -> str:
        username = super().clean_username()
        validate_username_not_blocked(username)
        if is_identity_blocked(username=username):
            raise forms.ValidationError(_("This username is not available."))
        return username

    def clean_email(self) -> str:
        email = super().clean_email()
        if is_identity_blocked(email=email):
            raise forms.ValidationError(
                _("This email address cannot be used to sign up."),
            )
        return email

    def save(self, request):
        from neuromancers_network.core.audit import record_audit  # noqa: PLC0415
        from neuromancers_network.moderation.banning import (  # noqa: PLC0415
            email_is_banned,
        )

        user = super().save(request)
        user.accepted_tos = True
        update_fields = ["accepted_tos"]
        quarantined = email_is_banned(user.email)
        if quarantined:
            # Shadow quarantine: the account is created but held inactive and
            # flagged, and the ban is never disclosed to the signer.
            user.is_active = False
            update_fields.append("is_active")
        user.save(update_fields=update_fields)
        if quarantined:
            try:
                record_audit(
                    action="moderation.email_ban_quarantine",
                    actor=user,
                    user=user,
                    request=request,
                )
            except Exception:
                logger.exception("Failed to audit email-ban quarantine")
        return user


class AddEmailForm(BaseAddEmailForm):
    """allauth add-email form with an admin-configurable change cooldown."""

    def clean_email(self) -> str:
        value = super().clean_email()
        ensure_email_change_allowed(getattr(self, "user", None))
        return value
