from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition

from .users import User


class Profile(models.Model):
    """Profile — extended user information."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )
    bio = models.TextField(blank=True)
    languages = models.JSONField(
        default=list,
        blank=True,
        help_text="e.g. ['en', 'fr']",
    )
    country = models.CharField(max_length=2, blank=True)
    avatar_id = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("GetPronto file ID for the profile picture"),
    )
    tier_state = FSMField(
        default="seeker",
        choices=[
            ("seeker", "Seeker"),
            ("peer", "Peer"),
            ("verified_peer", "Verified Peer"),
        ],
        protected=True,
    )
    default_tos = models.TextField(
        blank=True,
        help_text="Default terms shown to attendees",
    )
    default_needs = models.TextField(
        blank=True,
        help_text="Default accessibility needs",
    )
    notification_prefs = models.JSONField(default=dict, blank=True)
    has_customized = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile({self.user.username})"

    # -- FSM transitions ---------------------------------------------------

    @transition(field=tier_state, source="seeker", target="peer")
    def promote_to_peer(self):
        """Move from Seeker to Peer."""

    @transition(field=tier_state, source="peer", target="verified_peer")
    def promote_to_verified_peer(self):
        """Move from Peer to Verified Peer."""

    @transition(field=tier_state, source=["peer", "verified_peer"], target="seeker")
    def demote_to_seeker(self):
        """Demote back to Seeker."""

    @transition(field=tier_state, source="verified_peer", target="peer")
    def demote_to_peer(self):
        """Demote back to Peer."""
