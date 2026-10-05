from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped

from .request import MeetingRequest


class Review(Timestamped):
    meeting_request = models.OneToOneField(
        MeetingRequest,
        on_delete=models.CASCADE,
        related_name="review",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_given",
    )
    peer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
    rating = models.PositiveIntegerField(
        _("Rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(_("Comment"), blank=True)
    is_published = models.BooleanField(_("Published"), default=True)

    @property
    def display_title(self) -> str:
        return f"Review of {self.peer.display_name}"

    @property
    def is_live(self) -> bool:
        return bool(self.is_published)

    def get_absolute_url(self) -> str:
        from django.contrib.contenttypes.models import ContentType  # noqa: PLC0415

        from neuromancers_network.core.models.pages import (  # noqa: PLC0415
            ReviewDetailPage,
        )

        page = ReviewDetailPage.objects.filter(
            source_content_type=ContentType.objects.get_for_model(type(self)),
            source_object_id=self.pk,
            live=True,
        ).first()
        if page is not None:
            url = page.get_url()
            if url:
                return url
        return f"/reviews/{self.pk}/"
