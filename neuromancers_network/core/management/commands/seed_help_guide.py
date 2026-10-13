"""Seed the admin help guide categories, articles and glossary.

Content lives in ``core/help_seed.yaml``. Idempotent: existing rows are left
untouched unless ``--force`` is passed, so admin edits are never clobbered by a
re-run.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from neuromancers_network.core.help_seed import HelpSeedError
from neuromancers_network.core.help_seed import load_help_spec
from neuromancers_network.core.models import GlossaryTerm
from neuromancers_network.core.models import HelpArticle
from neuromancers_network.core.models import HelpCategory


def _apply(obj: Any, defaults: dict, *, force: bool) -> bool:
    """Fill a newly created row, or overwrite it when *force* is set.

    Returns ``True`` if the row changed.
    """
    if not force:
        return False
    changed = False
    for field, value in defaults.items():
        if getattr(obj, field) != value:
            setattr(obj, field, value)
            changed = True
    if changed:
        obj.save()
    return changed


def _sync(model, lookup: dict, defaults: dict, *, force: bool) -> tuple[bool, bool]:
    """Get-or-create one row. Returns ``(created, updated)``."""
    obj, was_created = model.objects.get_or_create(**lookup, defaults=defaults)
    if was_created:
        return True, False
    return False, _apply(obj, defaults, force=force)


def _seed_categories(
    specs: list,
    *,
    force: bool,
) -> tuple[dict[str, HelpCategory], int, int]:
    categories: dict[str, HelpCategory] = {}
    created = updated = 0
    for spec in specs:
        defaults = {
            "name": spec["name"],
            "description": spec["description"],
            "icon": spec["icon"],
            "sort_order": spec["sort_order"],
        }
        category, was_created = HelpCategory.objects.get_or_create(
            slug=spec["slug"],
            defaults=defaults,
        )
        did_update = False if was_created else _apply(category, defaults, force=force)
        created += int(was_created)
        updated += int(did_update)
        categories[spec["slug"]] = category
    return categories, created, updated


def _seed_articles(
    specs: list,
    categories: dict[str, HelpCategory],
    *,
    force: bool,
) -> tuple[int, int]:
    created = updated = 0
    for spec in specs:
        category = categories.get(spec["category"])
        if category is None:
            continue
        defaults = {
            "title": spec["title"],
            "category": category,
            "kind": spec["kind"],
            "audience": spec["audience"],
            "summary": spec["summary"],
            "body": spec["body"],
            "steps": spec["steps"],
            "sort_order": spec["sort_order"],
            "is_published": spec["is_published"],
        }
        was_created, did_update = _sync(
            HelpArticle,
            {"slug": spec["slug"]},
            defaults,
            force=force,
        )
        created += int(was_created)
        updated += int(did_update)
    return created, updated


def _seed_glossary(specs: list, *, force: bool) -> tuple[int, int]:
    created = updated = 0
    for spec in specs:
        was_created, did_update = _sync(
            GlossaryTerm,
            {"term": spec["term"]},
            {"definition": spec["definition"], "aliases": spec["aliases"]},
            force=force,
        )
        created += int(was_created)
        updated += int(did_update)
    return created, updated


def seed_help(*, force: bool = False) -> dict[str, int]:
    """Create missing help content. Returns counts of created/updated rows."""
    spec = load_help_spec()
    categories, created_c, updated_c = _seed_categories(
        spec["categories"],
        force=force,
    )
    created_a, updated_a = _seed_articles(spec["articles"], categories, force=force)
    created_g, updated_g = _seed_glossary(spec["glossary"], force=force)
    return {
        "created": created_c + created_a + created_g,
        "updated": updated_c + updated_a + updated_g,
    }


class Command(BaseCommand):
    help = "Seed the admin help guide (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing rows with the seed values.",
        )

    def handle(self, *args, **options):
        try:
            counts = seed_help(force=options["force"])
        except HelpSeedError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Help guide seeded: {counts['created']} created, "
                f"{counts['updated']} updated.",
            ),
        )
