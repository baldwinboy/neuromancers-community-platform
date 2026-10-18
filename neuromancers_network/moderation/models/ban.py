from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class EmailBan(Timestamped):
    """A banned email address or whole domain (enforced with shadow quarantine)."""

    value = models.CharField(
        _("Email or domain"),
        max_length=255,
        unique=True,
        help_text=_("An email address, or a domain when 'Whole domain' is set."),
    )
    is_domain = models.BooleanField(
        _("Whole domain"),
        default=False,
        help_text=_("Match any address at this domain, e.g. example.com."),
    )
    reason = models.TextField(_("Reason"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Email ban")
        verbose_name_plural = _("Email bans")

    def _normalise(self) -> None:
        self.value = (self.value or "").strip().lower()

    def clean(self):
        super().clean()
        self._normalise()

    def save(self, *args, **kwargs):
        self._normalise()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.value


class IPBan(Timestamped):
    """A single banned IP address, optionally time-boxed."""

    ip_address = models.GenericIPAddressField(_("IP address"), unique=True)
    reason = models.TextField(_("Reason"), blank=True)
    expires_at = models.DateTimeField(
        _("Expires at"),
        null=True,
        blank=True,
        help_text=_("Leave empty for no expiry."),
    )

    class Meta:
        verbose_name = _("IP ban")
        verbose_name_plural = _("IP bans")

    def __str__(self):
        return self.ip_address

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()
