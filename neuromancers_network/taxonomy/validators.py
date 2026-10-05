"""Validation for admin-curated tags and countries.

Values may be names/codes (``str``), primary keys, or model instances. Unknown
or inactive entries raise ``ValidationError`` so both forms and services reject
them before they reach the database.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from neuromancers_network.taxonomy.models import AllowedTag
from neuromancers_network.taxonomy.models import Country


def _resolve_tag(value):
    if isinstance(value, AllowedTag):
        return value
    text = str(value)
    tag = AllowedTag.objects.filter(name__iexact=text, is_active=True).first()
    if tag is None and text.isdigit():
        tag = AllowedTag.objects.filter(pk=int(text), is_active=True).first()
    return tag


def validate_allowed_tags(values) -> list[AllowedTag]:
    """Resolve *values* to active ``AllowedTag`` instances."""
    resolved = []
    invalid = []
    for value in values:
        tag = _resolve_tag(value)
        if tag is None or not tag.is_active:
            invalid.append(value)
        else:
            resolved.append(tag)
    if invalid:
        raise ValidationError(
            _("Unknown or inactive tags: %(tags)s")
            % {"tags": ", ".join(str(value) for value in invalid)},
            code="invalid_tags",
        )
    return resolved


def _resolve_country(value):
    if isinstance(value, Country):
        return value
    text = str(value)
    country = Country.objects.filter(code__iexact=text).first()
    if country is None and text.isdigit():
        country = Country.objects.filter(pk=int(text)).first()
    return country


def validate_countries(values) -> list[Country]:
    """Resolve *values* to ``Country`` instances."""
    resolved = []
    invalid = []
    for value in values:
        country = _resolve_country(value)
        if country is None:
            invalid.append(value)
        else:
            resolved.append(country)
    if invalid:
        raise ValidationError(
            _("Unknown countries: %(countries)s")
            % {"countries": ", ".join(str(value) for value in invalid)},
            code="invalid_countries",
        )
    return resolved
