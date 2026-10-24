import logging

from allauth.account.forms import AddEmailForm as BaseAddEmailForm
from allauth.account.forms import SignupForm
from allauth.account.models import EmailAddress
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from wagtail.users.forms import UserCreationForm as WagtailUserCreationForm
from wagtail.users.forms import UserEditForm as WagtailUserEditForm

from neuromancers_network.moderation.identity import is_identity_blocked
from neuromancers_network.users.cooldown import ensure_email_change_allowed
from neuromancers_network.users.utils import normalize_email
from neuromancers_network.users.utils import normalize_username
from neuromancers_network.users.validators import validate_username_not_blocked

logger = logging.getLogger(__name__)


User = get_user_model()


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
        self.cleaned_data["username"] = normalize_username(
            self.cleaned_data["username"],
        )
        username = super().clean_username()
        validate_username_not_blocked(username)
        if is_identity_blocked(username=username):
            raise forms.ValidationError(_("This username is not available."))
        return username

    def clean_email(self) -> str:
        self.cleaned_data["email"] = normalize_email(self.cleaned_data["email"])
        email = super().clean_email()
        if is_identity_blocked(email=email):
            raise forms.ValidationError(
                _("This email address cannot be used to sign up."),
            )
        return email

    def save(self, request):
        from neuromancers_network.core.audit import record_audit  # noqa: PLC0415
        from neuromancers_network.moderation.banning import email_is_banned  # noqa: PLC0415

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
        value = normalize_email(value)
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


class _NormalizeIdentityMixin:
    """Normalise identity fields and sync allauth after admin saves."""

    def _clean_username(self):
        if "username" in self.cleaned_data:
            self.cleaned_data["username"] = normalize_username(
                self.cleaned_data["username"],
            )
        return super()._clean_username()

    def clean_email(self) -> str:
        value = normalize_email(self.cleaned_data["email"])

        users = User._default_manager.filter(email__iexact=value)  # noqa: SLF001
        addresses = EmailAddress.objects.filter(email__iexact=value)
        if self.instance.pk is not None:
            users = users.exclude(pk=self.instance.pk)
            addresses = addresses.exclude(user_id=self.instance.pk)

        if value and users.exists():
            raise forms.ValidationError(
                _("A user with that email address already exists."),
            )
        if value and addresses.exists():
            raise forms.ValidationError(
                _("This email address is already in use."),
            )
        return value

    def save(self, commit=True):  # noqa: FBT002 - matches Wagtail's signature
        with transaction.atomic():
            is_new = self.instance.pk is None
            user = super().save(commit=commit)
            if commit and is_new:
                from neuromancers_network.users.services import sync_email_address  # noqa: PLC0415

                sync_email_address(user)
            return user


class UserCreationForm(
    _DropFullNameFieldsMixin,
    _NormalizeIdentityMixin,
    WagtailUserCreationForm,
):
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


class UserEditForm(
    _DropFullNameFieldsMixin,
    _NormalizeIdentityMixin,
    WagtailUserEditForm,
):
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
