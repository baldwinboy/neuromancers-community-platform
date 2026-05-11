from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from wagtail.images.models import AbstractImage
from wagtail.images.models import AbstractRendition
from wagtail.images.models import Filter
from wagtail.images.models import get_rendition_upload_to
from wagtail.images.models import get_upload_to

from neuromancers_network.common.getpronto import generate_transform_url
from neuromancers_network.common.image_operations import filter_to_transform_params
from neuromancers_network.common.storage import GetProntoStorage

if TYPE_CHECKING:
    from wagtail.images.models import AbstractRendition as AbstractRenditionType

default_storage = GetProntoStorage()


class AbstractGetProntoImage(AbstractImage):
    """
    Replaces Wagtail's file-based renditions with GetPronto on-the-fly transformations.
    """

    file = models.ImageField(
        verbose_name=_("file"),
        upload_to=get_upload_to,
        width_field="width",
        height_field="height",
        storage=default_storage,
    )

    # --------------------------------------------------------------
    # Ensure file hash & size are computed after upload
    # --------------------------------------------------------------
    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if not update_fields or "file" in update_fields:
            self._set_image_file_metadata()
        super().save(*args, **kwargs)

    def _set_image_file_metadata(self):
        # Only if the file has actually been saved (has an id)
        if self.file and not self.file_hash:
            self.file.open()
            self.file_size = self.file.size
            self._set_file_hash()
            self.file.seek(0)

    # --------------------------------------------------------------
    # SVG handling - keep Wagtail's behaviour
    # --------------------------------------------------------------
    def get_rendition(self, image_filter: Filter | str) -> AbstractRenditionType:
        if isinstance(image_filter, str):
            image_filter = Filter(spec=image_filter)
        image_filter = self.clean_filter_for_svg(image_filter)  # ← respect preserve-svg
        return super().get_rendition(image_filter)  # fall through to overridden methods

    # --------------------------------------------------------------
    # Override the entire rendition-creation pipeline
    # --------------------------------------------------------------
    def find_existing_rendition(self, image_filter: Filter) -> AbstractRenditionType:
        renditions = self.find_existing_renditions(image_filter)
        try:
            return renditions[image_filter]
        except KeyError:
            msg = f"No rendition found for filter '{image_filter.spec}'"
            raise self.get_rendition_model().DoesNotExist(
                msg,
            )

    def find_existing_renditions(
        self,
        *filters: Filter,
    ) -> dict[Filter, AbstractRenditionType]:
        rendition_model = self.get_rendition_model()
        filters_by_spec = {f.spec: f for f in filters}
        found = {}

        # 1. Try prefetched renditions (if any)
        prefetched = self._get_prefetched_renditions()
        if prefetched is not None:
            for rendition in prefetched:
                try:
                    f = filters_by_spec[rendition.filter_spec]
                except KeyError:
                    continue
                if rendition.focal_point_key == f.get_cache_key(self):
                    found[f] = rendition
            return found

        # 2. Try cache
        cache_keys = [
            rendition_model.construct_cache_key(self, f.get_cache_key(self), f.spec)
            for f in filters
        ]
        for rendition in rendition_model.cache_backend.get_many(cache_keys).values():
            # reconstruct filter from spec in rendition
            f = filters_by_spec[rendition.filter_spec]
            rendition.image = self  # re-attach current image instance
            found[f] = rendition

        # 3. Try database
        not_found = [f for f in filters if f not in found]
        if not_found:
            lookup = Q()
            for f in not_found:
                lookup |= Q(filter_spec=f.spec, focal_point_key=f.get_cache_key(self))
            for rendition in self.renditions.filter(lookup):
                f = filters_by_spec[rendition.filter_spec]
                found[f] = rendition
        return found

    def create_rendition(self, image_filter: Filter) -> AbstractRenditionType:
        transform = filter_to_transform_params(image_filter, self.width, self.height)
        cache_key = image_filter.get_cache_key(self)
        defaults = {
            "file": None,  # ← explicitly nullable
            "width": transform.w or self.width,
            "height": transform.h or self.height,
        }
        try:
            rendition, _created = self.renditions.get_or_create(
                filter_spec=image_filter.spec,
                focal_point_key=cache_key,
                defaults=defaults,
            )
        except Exception:  # race condition - try again  # noqa: BLE001
            rendition = self.renditions.get(
                filter_spec=image_filter.spec,
                focal_point_key=cache_key,
            )
        return rendition

    def get_renditions(
        self,
        *filters: Filter | str,
    ) -> dict[str, AbstractRenditionType]:
        rendition_model = self.get_rendition_model()
        clean_filters = [
            self.clean_filter_for_svg(Filter(spec=image_filter))
            if isinstance(image_filter, str)
            else self.clean_filter_for_svg(image_filter)
            for image_filter in filters
        ]
        # Remove duplicates, preserve order
        filters = list(dict.fromkeys(clean_filters))

        # Find existing
        renditions = self.find_existing_renditions(*filters)

        # Create missing
        not_found = [f for f in filters if f not in renditions]
        # Build them one by one (threading not needed here)
        for f in not_found:
            # Use create_rendition - it handles get_or_create + defaults
            renditions[f] = self.create_rendition(f)

        # Update cache
        cache_additions = {
            rendition_model.construct_cache_key(
                self,
                f.get_cache_key(self),
                f.spec,
            ): renditions[f]
            for f in renditions
            if not getattr(renditions[f], "_from_cache", False)
        }
        if cache_additions:
            rendition_model.cache_backend.set_many(cache_additions)

        # Return spec→rendition dict, preserving input order
        return {f.spec: renditions[f] for f in filters}

    class Meta(AbstractImage.Meta):
        abstract = True


class AbstractGetProntoRendition(AbstractRendition):
    """
    Stores only metadata. The image is generated on-the-fly by GetPronto.
    The ``file`` field exists to keep Django happy, but is never used.
    """

    file = models.ImageField(
        verbose_name=_("file"),
        upload_to=get_rendition_upload_to,
        storage=default_storage,
        width_field="width",
        height_field="height",
        null=True,  # ← critical: allows DB rows without a file
        blank=True,
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
        abstract = True

    @property
    def url(self) -> str:
        image_filter = Filter(spec=self.filter_spec)
        transform = filter_to_transform_params(
            image_filter,
            self.image.width,
            self.image.height,
        )
        file_id = self.image.file.name  # the GetPronto file ID
        return generate_transform_url(
            api_key=default_storage.get_api_key(),
            image_id=file_id,
            transform_params=transform,
        )

    @property
    def img_tag(self) -> str:
        return (
            f'<img src="{self.url}" width="{self.width}" height="{self.height}" alt="">'
        )
