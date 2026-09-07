from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager

from neuromancers_network.core.models import Timestamped


class PeerProfile(Timestamped):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="peer_profile",
    )
    bio = models.TextField(_("Bio"), blank=True)
    # Profile picture lives on UserProfile (all users get one)
    languages = models.ManyToManyField(
        "taxonomy.Language",
        blank=True,
        related_name="peers",
    )
    tags = TaggableManager(blank=True)

    # Peer approval
    is_approved = models.BooleanField(_("Approved by moderator"), default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_peers",
    )
    approved_at = models.DateTimeField(_("Approved at"), null=True, blank=True)

    # Peer verification
    is_verified = models.BooleanField(_("Verified by moderator"), default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_peers",
    )
    verified_at = models.DateTimeField(_("Verified at"), null=True, blank=True)

    class Meta:
        verbose_name = "Peer profile"
        verbose_name_plural = "Peer profiles"
