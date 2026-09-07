from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition

from .choices import StaffState


class User(AbstractUser):
    """
    Minimal user model for account management.
    All users have support seeker capabilities by default.
    Moderators are identified by staff_state (FSM-controlled).
    """

    name = models.CharField(_("Full name"), blank=True, max_length=255)
    date_of_birth = models.DateField(_("Date of Birth"), null=True, blank=True)
    accepted_tos = models.BooleanField(
        _("Accepted Terms of Service"),
        default=False,
        help_text=_("Whether the user has accepted the terms of service."),
    )
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    # FSM-controlled staff status
    staff_state = FSMField(
        _("Staff state"),
        default=StaffState.INACTIVE,
        choices=StaffState.choices,
        protected=True,
    )

    @property
    def is_staff(self) -> bool:  # type: ignore[override]
        return self.staff_state == StaffState.ACTIVE

    @is_staff.setter
    def is_staff(self, value: bool) -> None:
        if value:
            self.staff_state = StaffState.ACTIVE
        else:
            self.staff_state = StaffState.INACTIVE

    @transition(field=staff_state, source=StaffState.INACTIVE, target=StaffState.ACTIVE)
    def activate_staff(self):
        pass

    @transition(
        field=staff_state,
        source=StaffState.ACTIVE,
        target=StaffState.SUSPENDED,
    )
    def suspend_staff(self):
        pass

    @transition(
        field=staff_state,
        source=StaffState.SUSPENDED,
        target=StaffState.ACTIVE,
    )
    def reinstate_staff(self):
        pass

    def get_absolute_url(self) -> str:
        return reverse("users:detail", kwargs={"username": self.username})

    class Meta:
        pass

    @property
    def is_peer(self) -> bool:
        peer_profile = getattr(self, "peer_profile", None)
        payment_profile = getattr(self, "payment_profile", None)
        return (
            peer_profile is not None
            and peer_profile.is_approved
            and payment_profile is not None
            and payment_profile.has_active_subscription
            and payment_profile.kyc_completed
        )

    @property
    def is_verified_peer(self) -> bool:
        peer_profile = getattr(self, "peer_profile", None)
        return self.is_peer and peer_profile is not None and peer_profile.is_verified
