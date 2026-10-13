import logging

from allauth.account.forms import AddEmailForm as BaseAddEmailForm
from allauth.account.forms import SignupForm
from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.users.forms import UserCreationForm as WagtailUserCreationForm
from wagtail.users.forms import UserEditForm as WagtailUserEditForm

from neuromancers_network.moderation.identity import is_identity_blocked
from neuromancers_network.users.cooldown import ensure_email_change_allowed
from neuromancers_network.users.validators import validate_username_not_blocked

logger = logging.getLogger(__name__)


class UserSignupForm(SignupForm):
    """
    Form rendered on the user sign up screen.

    allauth contributes the native fields (username, email, password) from
    ``ACCOUNT_SIGNUP_FIELDS``; the project fields below are declared here and
    persisted onto the user in :meth:`save`.
    """

    name = forms.CharField(label=_("Full name"), max_length=255)
    date_of_birth = forms.DateField(
        label=_("Date of birth"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    accepted_tos = forms.BooleanField(
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
        user.name = self.cleaned_data["name"]
        user.date_of_birth = self.cleaned_data["date_of_birth"]
        user.accepted_tos = self.cleaned_data["accepted_tos"]
        update_fields = ["name", "date_of_birth", "accepted_tos"]
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


class _DropFullNameFieldsMixin:
    """Drop the inherited ``first_name``/``last_name`` form fields.

    Wagtail's user forms declare them on the base form class, so they survive
    ``Meta.fields`` changes and must be removed explicitly. The project collects
    a single ``name`` field instead.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("first_name", None)
        self.fields.pop("last_name", None)


class UserCreationForm(_DropFullNameFieldsMixin, WagtailUserCreationForm):
    """Wagtail admin user-create form using the project's ``name`` field."""

    name = forms.CharField(required=True, label=_("Full name"), max_length=255)
    date_of_birth = forms.DateField(
        required=False,
        label=_("Date of birth"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta(WagtailUserCreationForm.Meta):
        fields = (WagtailUserCreationForm.Meta.fields - {"first_name", "last_name"}) | {
            "name",
            "date_of_birth",
        }


class UserEditForm(_DropFullNameFieldsMixin, WagtailUserEditForm):
    """Wagtail admin user-edit form using the project's ``name`` field."""

    name = forms.CharField(required=True, label=_("Full name"), max_length=255)
    date_of_birth = forms.DateField(
        required=False,
        label=_("Date of birth"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta(WagtailUserEditForm.Meta):
        fields = (WagtailUserEditForm.Meta.fields - {"first_name", "last_name"}) | {
            "name",
            "date_of_birth",
        }
