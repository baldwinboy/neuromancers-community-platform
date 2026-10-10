"""Load ISO countries and languages from the CLDR registry (via Babel).

The taxonomy tables are admin-curated, so the loaders are intentionally
idempotent: existing rows are matched by ``code`` and updated in place, and
rows whose name clashes with another entry are skipped rather than aborting the
whole import.
"""

from __future__ import annotations

import logging

from babel import Locale
from babel.core import UnknownLocaleError
from django.db import IntegrityError
from django.db import transaction

from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import Language

logger = logging.getLogger(__name__)

# ISO 3166-1 alpha-2 and ISO 639-1 codes are both two letters long.
CODE_LENGTH = 2


def country_rows() -> list[tuple[str, str]]:
    """Return ``(code, name)`` for every ISO 3166-1 alpha-2 country."""
    territories = Locale("en").territories
    return sorted(
        (code, name)
        for code, name in territories.items()
        if len(code) == CODE_LENGTH and code.isalpha() and code.isupper()
    )


def language_rows() -> list[tuple[str, str, str]]:
    """Return ``(code, name, name_local)`` for every ISO 639-1 language."""
    languages = Locale("en").languages
    rows = []
    for code, name in languages.items():
        if len(code) != CODE_LENGTH or not code.isalpha() or not code.islower():
            continue
        rows.append((code, name, _endonym(code) or name))
    return sorted(rows)


def _endonym(code: str) -> str:
    try:
        return Locale.parse(code).display_name or ""
    except UnknownLocaleError, ValueError, TypeError:
        return ""


def load_countries() -> tuple[int, int, int]:
    """Upsert every ISO country; return ``(created, updated, skipped)``."""
    return _upsert(
        Country,
        ((code, {"name": name}) for code, name in country_rows()),
    )


def load_languages() -> tuple[int, int, int]:
    """Upsert every ISO 639-1 language; return ``(created, updated, skipped)``."""
    return _upsert(
        Language,
        (
            (code, {"name": name, "name_local": name_local})
            for code, name, name_local in language_rows()
        ),
    )


def _upsert(model, rows) -> tuple[int, int, int]:
    created = updated = skipped = 0
    for code, defaults in rows:
        try:
            with transaction.atomic():
                _obj, was_created = model.objects.update_or_create(
                    code=code,
                    defaults=defaults,
                )
        except IntegrityError:
            skipped += 1
            logger.warning("Skipped %s %r: duplicate name", model.__name__, code)
            continue
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated, skipped
