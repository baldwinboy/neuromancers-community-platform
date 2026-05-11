from datetime import datetime

from dateutil import relativedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

MIN_AGE = 18


class User(AbstractUser):
    """
    Default custom user model for Neuromancers Network.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Full name"), blank=True, max_length=255)
    date_of_birth = models.DateField(_("Date of Birth"), null=True, blank=True)
    accepted_tos = models.BooleanField(
        _("Accepted Terms of Service"),
        default=False,
        help_text=_("Whether the user has accepted the terms of service."),
    )
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    stripe_account = models.ForeignKey(
        "djstripe.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text=_("Stripe Connect account for receiving payments"),
    )

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    def clean_date_of_birth(self):
        """Validate that the user is at least MIN_AGE years old."""
        dob = self.cleaned_data.get("date_of_birth")
        if dob:
            today = datetime.datetime.now(tz=datetime.UTC).date()
            age = relativedelta.relativedelta(today, dob)
            if age.years < MIN_AGE:
                raise ValidationError(
                    _(
                        "You must be at least %(min_age)d years old to register.",
                    )
                    % {"min_age": MIN_AGE},
                )

    def clean(self):
        """Validate against admin-controlled blocklist."""
        cleaned = super().clean()
        blocklist = [b.lower() for b in settings.BLOCKED_USERNAMES]

        if cleaned.get("name", "").lower() in blocklist:
            raise ValidationError(
                _("This name is not allowed."), code="invalid_user_name"
            )

        if cleaned.get("username", "").lower() in blocklist:
            raise ValidationError(
                _("This username is not allowed."), code="invalid_user_username"
            )


def get_anonymous_user_instance(User):  # noqa: N803
    """Return an unsaved Guardian anonymous user instance.

    Required by django-guardian's ``GUARDIAN_GET_INIT_ANONYMOUS_USER`` setting
    when using a custom User model.
    """
    user = User(username=settings.ANONYMOUS_USER_NAME, is_active=False)
    user.set_unusable_password()
    return user
