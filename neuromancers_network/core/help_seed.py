"""Load the Admin Guide starter catalogue from ``help_seed.yaml``.

The catalogue is data, not code: keep prose edits in the YAML file next to this
module. This module reads and validates that file and shapes article bodies and
steps into the dicts the ``StreamField`` fields expect. The
``seed_help_guide`` command consumes :func:`load_help_spec`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import yaml

DEFAULT_PATH = Path(__file__).with_name("help_seed.yaml")

_BODY_TYPES = frozenset({"header", "text", "rich_text"})
#: ``HelpCategory.slug``/``HelpArticle.slug`` are ``SlugField`` (default max length).
_MAX_SLUG_LENGTH = 50


class HelpSeedError(ValueError):
    """Raised when the help catalogue data file is missing or malformed."""


class CategorySpec(TypedDict):
    name: str
    slug: str
    description: str
    icon: str
    sort_order: int


class ArticleSpec(TypedDict):
    title: str
    slug: str
    category: str
    kind: str
    audience: str
    summary: str
    body: list[dict]
    steps: list[dict]
    sort_order: int
    is_published: bool


class GlossarySpec(TypedDict):
    term: str
    definition: str
    aliases: str


class HelpSpec(TypedDict):
    categories: list[CategorySpec]
    articles: list[ArticleSpec]
    glossary: list[GlossarySpec]


def load_help_spec(path: str | Path = DEFAULT_PATH) -> HelpSpec:
    """Read, validate and shape the help catalogue from *path*.

    Raises :class:`HelpSeedError` on a missing file or malformed content, so a
    broken catalogue fails loudly rather than seeding partial data.
    """
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        message = f"Help seed file not found: {path}"
        raise HelpSeedError(message) from exc
    except yaml.YAMLError as exc:
        message = f"Help seed file is not valid YAML: {exc}"
        raise HelpSeedError(message) from exc

    if not isinstance(raw, dict):
        message = (
            "Help seed file must contain a mapping of categories/articles/glossary."
        )
        raise HelpSeedError(message)

    categories = _categories(raw.get("categories"))
    category_slugs = {category["slug"] for category in categories}
    articles = _articles(raw.get("articles"), category_slugs)
    glossary = _glossary(raw.get("glossary"))
    return HelpSpec(categories=categories, articles=articles, glossary=glossary)


def _text(data: dict, key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        message = f"{where} needs a non-empty '{key}'."
        raise HelpSeedError(message)
    return value


def _slug(data: dict, where: str) -> str:
    slug = _text(data, "slug", where)
    if len(slug) > _MAX_SLUG_LENGTH:
        message = (
            f"{where} slug {slug!r} is {len(slug)} characters; the model's "
            f"SlugField allows {_MAX_SLUG_LENGTH}."
        )
        raise HelpSeedError(message)
    return slug


def _categories(raw: object) -> list[CategorySpec]:
    if not isinstance(raw, list):
        message = "'categories' must be a list."
        raise HelpSeedError(message)
    result: list[CategorySpec] = []
    for index, item in enumerate(raw):
        where = f"categories[{index}]"
        if not isinstance(item, dict):
            message = f"{where} must be a mapping."
            raise HelpSeedError(message)
        result.append(
            CategorySpec(
                name=_text(item, "name", where),
                slug=_slug(item, where),
                description=str(item.get("description", "")),
                icon=str(item.get("icon", "")),
                sort_order=int(item.get("sort_order", 0)),
            ),
        )
    return result


def _articles(raw: object, category_slugs: set[str]) -> list[ArticleSpec]:
    if not isinstance(raw, list):
        message = "'articles' must be a list."
        raise HelpSeedError(message)
    result: list[ArticleSpec] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        where = f"articles[{index}]"
        if not isinstance(item, dict):
            message = f"{where} must be a mapping."
            raise HelpSeedError(message)
        slug = _slug(item, where)
        if slug in seen:
            message = f"{where} duplicates slug {slug!r}."
            raise HelpSeedError(message)
        seen.add(slug)
        category = _text(item, "category", where)
        if category not in category_slugs:
            message = f"{where} references unknown category {category!r}."
            raise HelpSeedError(message)
        result.append(
            ArticleSpec(
                title=_text(item, "title", where),
                slug=slug,
                category=category,
                kind=str(item.get("kind", "reference")),
                audience=str(item.get("audience", "")),
                summary=str(item.get("summary", "")),
                body=_body(item.get("body"), where),
                steps=_steps(item.get("steps"), where),
                sort_order=int(item.get("sort_order", 0)),
                is_published=bool(item.get("is_published", False)),
            ),
        )
    return result


def _body(raw: object, where: str) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        message = f"{where}.body must be a list."
        raise HelpSeedError(message)
    entries: list[dict] = []
    for position, entry in enumerate(raw):
        if not isinstance(entry, dict):
            message = f"{where}.body[{position}] must be a mapping."
            raise HelpSeedError(message)
        block_type = entry.get("type")
        if block_type not in _BODY_TYPES:
            message = f"{where}.body[{position}] has unknown type {block_type!r}."
            raise HelpSeedError(message)
        text = entry.get("text")
        if not isinstance(text, str) or not text:
            message = f"{where}.body[{position}] needs non-empty 'text'."
            raise HelpSeedError(message)
        entries.append({"type": block_type, "value": {"text": text}})
    return entries


def _steps(raw: object, where: str) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        message = f"{where}.steps must be a list."
        raise HelpSeedError(message)
    entries: list[dict] = []
    for position, entry in enumerate(raw):
        if not isinstance(entry, dict):
            message = f"{where}.steps[{position}] must be a mapping."
            raise HelpSeedError(message)
        text = entry.get("text")
        if not isinstance(text, str) or not text:
            message = f"{where}.steps[{position}] needs non-empty 'text'."
            raise HelpSeedError(message)
        entries.append(
            {
                "type": "step",
                "value": {"text": text, "callout": str(entry.get("callout", ""))},
            },
        )
    return entries


def _glossary(raw: object) -> list[GlossarySpec]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        message = "'glossary' must be a list."
        raise HelpSeedError(message)
    result: list[GlossarySpec] = []
    for index, item in enumerate(raw):
        where = f"glossary[{index}]"
        if not isinstance(item, dict):
            message = f"{where} must be a mapping."
            raise HelpSeedError(message)
        result.append(
            GlossarySpec(
                term=_text(item, "term", where),
                definition=_text(item, "definition", where),
                aliases=str(item.get("aliases", "")),
            ),
        )
    return result
