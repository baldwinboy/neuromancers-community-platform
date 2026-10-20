from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped

from .choices import ReviewStatus
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
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PUBLISHED,
        db_index=True,
    )

    @property
    def display_title(self) -> str:
        return f"Review of {self.peer.display_name}"

    @property
    def is_live(self) -> bool:
        return self.status == ReviewStatus.PUBLISHED

    def publish(self) -> None:
        self.status = ReviewStatus.PUBLISHED

    def hide(self) -> None:
        self.status = ReviewStatus.HIDDEN

    def get_absolute_url(self) -> str:
        from django.contrib.contenttypes.models import ContentType  # noqa: PLC0415

        from neuromancers_network.core.models.pages import ReviewDetailPage  # noqa: PLC0415
        from neuromancers_network.core.models.pages import ReviewIndexPage  # noqa: PLC0415

        page = ReviewDetailPage.objects.filter(
            source_content_type=ContentType.objects.get_for_model(type(self)),
            source_object_id=self.pk,
            live=True,
        ).first()
        if page is not None:
            url = page.get_url()
            if url:
                return url
        index = ReviewIndexPage.objects.live().first()
        if index is not None:
            url = index.get_url()
            if url:
                return url
        return "/"
