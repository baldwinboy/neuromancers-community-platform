from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager
from wagtail.search import index

from neuromancers_network.core.models import Timestamped

from .tag import PeerProfileTag


class PeerProfile(index.Indexed, Timestamped):  # type: ignore[django-manager-missing]
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
    countries = models.ManyToManyField(
        "taxonomy.Country",
        blank=True,
        related_name="peers",
        verbose_name=_("Countries"),
    )
    tags = TaggableManager(
        blank=True,
        through=PeerProfileTag,
        to="taxonomy.AllowedTag",
    )

    # Peer terms & conditions — offered to seekers, snapshotted per request
    default_terms = models.TextField(_("Default terms & conditions"), blank=True)
    default_terms_updated_at = models.DateTimeField(
        _("Terms updated at"),
        null=True,
        blank=True,
    )

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
        indexes = [
            models.Index(fields=["is_approved"], name="peers_peerprofile_approved_idx"),
        ]

    search_fields = [
        index.SearchField("bio"),
        index.RelatedFields("user", [index.SearchField("name")]),
        index.FilterField("is_approved"),
        index.FilterField("is_verified"),
        index.RelatedFields("countries", [index.FilterField("code")]),
        index.RelatedFields("languages", [index.FilterField("code")]),
        index.RelatedFields(
            "tags",
            [index.FilterField("is_active"), index.FilterField("slug")],
        ),
    ]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = (
                PeerProfile.objects.filter(pk=self.pk)
                .values_list("default_terms", flat=True)
                .first()
            )
            if previous is not None and previous != self.default_terms:
                self.default_terms_updated_at = timezone.now()
        super().save(*args, **kwargs)

    def verify(self, reviewer=None):
        self.is_verified = True
        self.verified_by = reviewer
        self.verified_at = timezone.now()
        self.save(
            update_fields=[
                "is_verified",
                "verified_by",
                "verified_at",
                "updated_at",
            ],
        )

    def unverify(self, reviewer=None):
        self.is_verified = False
        self.verified_by = reviewer
        self.verified_at = timezone.now()
        self.save(
            update_fields=[
                "is_verified",
                "verified_by",
                "verified_at",
                "updated_at",
            ],
        )

    @property
    def display_title(self) -> str:
        return self.user.display_name

    @property
    def username(self) -> str:
        return self.user.username

    @property
    def is_live(self) -> bool:
        return bool(self.is_approved)

    def get_absolute_url(self) -> str:
        from django.contrib.contenttypes.models import ContentType  # noqa: PLC0415

        from neuromancers_network.core.models.pages import (  # noqa: PLC0415
            PeerProfileDetailPage,
        )

        page = PeerProfileDetailPage.objects.filter(
            source_content_type=ContentType.objects.get_for_model(type(self)),
            source_object_id=self.pk,
            live=True,
        ).first()
        if page is not None:
            url = page.get_url()
            if url:
                return url
        return f"/peers/{self.user.username}/"
