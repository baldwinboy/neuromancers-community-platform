"""Reusable form mixins for admin-curated taxonomy fields."""

from __future__ import annotations

from typing import Any

from neuromancers_network.taxonomy.validators import validate_allowed_tags
from neuromancers_network.taxonomy.validators import validate_countries


class AllowedTagsCountriesFormMixin:
    """Validate ``tags`` and ``countries`` fields against the taxonomy."""

    cleaned_data: dict[str, Any]

    def clean_tags(self):
        tags = self.cleaned_data.get("tags") or []
        names = [getattr(tag, "name", tag) for tag in tags]
        return [tag.name for tag in validate_allowed_tags(names)]

    def clean_countries(self):
        countries = self.cleaned_data.get("countries") or []
        return validate_countries(list(countries))
