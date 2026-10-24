from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import FSMModelMixin
from django_fsm import transition
from wagtail.search import index

from neuromancers_network.users.utils import normalize_email
from neuromancers_network.users.utils import normalize_username

from .choices import StaffState


class User(FSMModelMixin, index.Indexed, AbstractUser):
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
    username_changed_at = models.DateTimeField(
        _("Username changed at"),
        null=True,
        blank=True,
        help_text=_("When the member last changed their username."),
    )
    email_changed_at = models.DateTimeField(
        _("Email changed at"),
        null=True,
        blank=True,
        help_text=_("When the member last changed their primary email address."),
    )
    deactivated_at = models.DateTimeField(
        _("Deactivated at"),
        null=True,
        blank=True,
        help_text=_("When the member deactivated their account."),
    )
    deactivation_reason = models.TextField(
        _("Deactivation reason"),
        blank=True,
        help_text=_("Optional reason recorded when the account was deactivated."),
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
    def is_staff(self) -> bool:
        return self.staff_state == StaffState.ACTIVE

    @is_staff.setter
    def is_staff(self, value: bool) -> None:
        # ``staff_state`` is a protected FSM field. Write through ``__dict__``
        # exactly as django-fsm does in its own transitions, so the standard
        # Django ``create_user``/``create_superuser`` paths (and factories)
        # work without raising a protected-field error.
        self.__dict__["staff_state"] = (
            StaffState.ACTIVE if value else StaffState.INACTIVE
        )

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

    @property
    def display_name(self) -> str:
        return self.name or self.username

    def get_full_name(self) -> str:
        """Return the member's full name.

        ``first_name``/``last_name`` are removed (set to ``None``) in favour of
        ``name``; overriding this avoids the inherited implementation rendering
        ``"None None"`` in the Wagtail admin and elsewhere.
        """
        return self.name or ""

    def get_short_name(self) -> str:
        return self.name or ""

    def get_absolute_url(self) -> str:
        from django.contrib.contenttypes.models import ContentType  # noqa: PLC0415

        from neuromancers_network.core.models import pages  # noqa: PLC0415

        page = pages.UserProfilePage.objects.filter(
            source_content_type=ContentType.objects.get_for_model(type(self)),
            source_object_id=self.pk,
            live=True,
        ).first()
        if page is not None:
            url = page.get_url()
            if url:
                return url
        index = pages.ProfileIndexPage.objects.live().first()
        if index is not None:
            url = index.get_url()
            if url:
                return url
        return "/"

    search_fields = [
        index.SearchField("name"),
        index.SearchField("username"),
    ]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="users_user_username_ci_unique",
            ),
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="users_user_email_ci_unique",
            ),
        ]

    def clean(self):
        super().clean()
        self.username = normalize_username(self.username)
        self.email = normalize_email(self.email)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is None:
            self.username = normalize_username(self.username)
            self.email = normalize_email(self.email)
        else:
            fields = set(update_fields)
            if "username" in fields:
                self.username = normalize_username(self.username)
            if "email" in fields:
                self.email = normalize_email(self.email)
        super().save(*args, **kwargs)

    @property
    def is_moderator(self) -> bool:
        return bool(self.is_staff or self.is_superuser)

    @property
    def is_deactivated(self) -> bool:
        return self.deactivated_at is not None

    @property
    def is_peer(self) -> bool:
        from neuromancers_network.peers.services import is_eligible_peer  # noqa: PLC0415

        return is_eligible_peer(self)

    @property
    def is_verified_peer(self) -> bool:
        peer_profile = getattr(self, "peer_profile", None)
        return self.is_peer and peer_profile is not None and peer_profile.is_verified
