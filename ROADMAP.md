# ROADMAP — Page-tree feeds, curated page tags, and tag pages

> **Audience:** agentic coding tools. This document is self-contained. Follow the
> work packages in order. Every file path, symbol, setting and command needed is
> given inline. Do not re-plan; implement exactly as specified and run the
> verification section at the end.

---

## 1. Objective

Let administrators build blog-like page structures on `StandardPage` **without a
new page-index model**, by:

1. **Four page-tree feeds** that can be dropped into any `StandardPage` body:
   - **Site-wide** — every eligible content page across all sites.
   - **All descendants** — every eligible descendant of the host page.
   - **Immediate children** — direct children of the host page.
   - **Deeper** — descendants of the host page excluding its immediate children
     (grandchildren and deeper).
2. **Curated page tags** — tag `StandardPage` using the existing `taxonomy.AllowedTag`
   taxonomy (the same mechanism already used by `PeerProfile` and `Meeting`).
3. **Tag filtering** in the feeds (multi-select) with a **dedupe workaround**.
4. **Tag detail + index pages** — one navigable page per `AllowedTag`, generated
   automatically via the daisIE detail-pages system.

### Non-goals
- No new *feed/listing* page model (categories are tags + generated detail pages,
  not free-standing index page types).
- No changes to daisIE itself; all integration is via settings, selectors,
  template override, template tags, and project models.

---

## 2. Background: how the pieces work (read before coding)

All paths below are relative to the repo root `/Users/giraffe/neuromancers_network`.

### 2.1 daisIE feeds
- A page body is a `ContentBlock` stream = `PAGE_CONTENT_BLOCKS + DATA_BLOCKS`,
  including a `feed` block.
  `wagtail_daisIE/blocks/content.py:19-22`, `wagtail_daisIE/feeds/blocks_data.py:269-273`.
- `FeedBlock` renders a `wagtail_daisIE_feeds.Feed` snippet
  (`wagtail_daisIE/feeds/blocks_data.py:120-172`).
- The feed's base queryset is `config.get_queryset(request, page)` where `page` is
  the **served page**; falls back to `model._default_manager.all()`.
  `wagtail_daisIE/dynamic/registry.py:85-110`, `wagtail_daisIE/dynamic/feeds.py:42-52`,
  `wagtail_daisIE/feeds/blocks_data.py:143-154`.
- Filters are declarative, declared in the context-model settings
  (`filters` dict) and applied by `apply_filters`
  (`wagtail_daisIE/dynamic/feeds.py:172-244`).
- **Known limitation:** the AJAX endpoint calls `render_feed(feed, request, offset=...)`
  **without `page`** (`wagtail_daisIE/dynamic/views.py:115-137`). This is why the
  selector supports a `request.GET["page"]` fallback (see 2.4).
- The stock feed template is
  `wagtail_daisIE/templates/wagtail_daisIE/blocks/data/feed.html`. We override it.

### 2.2 Context models
- Registered in `WAGTAIL_DAISIE_CONTEXT_MODELS` (`config/settings/base.py:490-550`).
- A context model's `queryset` may be a dotted path / callable invoked as
  `queryset(request, page)` (`registry.py:85-110`).
- Configured context-model keys are copied into **block** template context via
  `ThemedBlock.get_context` → `copy_context_values`
  (`wagtail_daisIE/base_blocks/design.py:269-271`,
  `wagtail_daisIE/dynamic/context.py:17-29`). This is how the override template can
  access the host page (`host_page`).
- Context models are injected into the page context by
  `StyledPageMixin.get_context` → `add_daisie_context`
  (`wagtail_daisIE/pages.py:202-221`, `wagtail_daisIE/dynamic/mixins.py:15-26`).

### 2.3 Detail pages (auto-generated pages per model instance)
- Configured in `WAGTAIL_DAISIE_DETAIL_PAGES` (`config/settings/base.py:712-761`).
- daisIE connects `post_save`/`pre_delete` receivers in `AppConfig.ready`
  (`wagtail_daisIE/apps.py:22-28`), which call `sync_detail_page` /
  `delete_detail_page` (`wagtail_daisIE/detail_pages/bridges.py:73-118`).
- The generated page type must subclass `ModelDetailPage`
  (`wagtail_daisIE/detail_pages/models.py:64-145`); `lookup_field`, `title_source`,
  `slug_source`, `publish_field` drive field mapping.
- **Important:** a generated detail page inherits theme/background/design/bindings
  from the `template_page` but **not `body`**
  (`detail_pages/models.py:122-145`). Tag page content must be computed in
  `get_context` or hard-coded in the template.

### 2.4 The tag-filter dedupe workaround (critical)
daisIE's multi-choice filter does `queryset.filter(field__in=values)` with **no
`.distinct()`, causing duplicate rows on M2M joins
(`wagtail_daisIE/dynamic/feeds.py:198-210`). **Workaround:**

- Do **not** declare a `tags` filter in the context-model `filters` config.
- Apply tag filtering **inside the selector**, using a `pk__in` subquery over
  tagged `StandardPage`s. `pk__in` yields each page once (dedupe for free) and works
  on a base `Page` queryset (which cannot resolve the `tags` relation directly).
- Render the tag UI in the overridden feed template via a template tag.

### 2.5 Existing project patterns to mirror
- Curated-tag through-model: `neuromancers_network/peers/models/tag.py:5`,
  `neuromancers_network/meetings/models/tag.py:5`.
- `TaggableManager(to=..., through=...)`: `peers/models/profile.py:32-36`.
- Selector module style: `neuromancers_network/meetings/selectors.py:1-25`.
- Page models: `neuromancers_network/core/models/pages.py`.
- Template-tag module style: `neuromancers_network/core/templatetags/currency.py`.
- Detail-page config example: `config/settings/base.py:712-761`.
- Existing project template override precedent:
  `neuromancers_network/templates/wagtail_daisIE/blocks/navbar.html`.

### 2.6 Toolchain
- Python 3.14, Django 6.0.x, Wagtail 8.0.x, django-taggit 6.1.
- Ruff: single-line imports (`lint.isort.force-single-line = true`), default line
  length 88. Migrations are excluded from ruff.
- Tests: pytest (`--ds=config.settings.test --reuse-db`).
- Commands: `just manage <args>`, `just pytest [args]`, `just lint`.
  (`justfile:36-42,69-79`).

---

## 3. Work packages

Implement in the order shown.

### WP1 — Curated tags on `StandardPage`

**New file** `neuromancers_network/core/models/tag.py`:

```python
from django.db import models
from taggit.models import TaggedItemBase


class StandardPageTag(TaggedItemBase):
    """Concrete taggit through-model restricting page tags to ``AllowedTag``."""

    content_object = models.ForeignKey(
        "core.StandardPage",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        "taxonomy.AllowedTag",
        on_delete=models.CASCADE,
        related_name="standard_page_items",
    )
```

**Edit** `neuromancers_network/core/models/pages.py`:

1. Add imports at the top:

```python
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel

from neuromancers_network.core.models.tag import StandardPageTag
```

2. Replace the `StandardPage` class (currently `pages.py:49-50`) with:

```python
class StandardPage(ReservedSlugPage):
    template = "core/standard_page.html"
    tags = TaggableManager(
        blank=True,
        through=StandardPageTag,
        to="taxonomy.AllowedTag",
    )

    content_panels = [*ReservedSlugPage.content_panels, FieldPanel("tags")]
```

3. Add `"core.TagIndexPage"` to `HomePage.subpage_types`
   (currently `pages.py:31-46`). Keep every existing entry.

**Notes**
- `ReservedSlugPage.content_panels` resolves to `StyledPageMixin.content_panels`.
- The tags M2M is concrete; tags save on the live page and are **not revisioned**
  (accepted limitation).

---

### WP2 — Tag index/detail page models

**Edit** `neuromancers_network/core/models/pages.py` (append after
`ReviewDetailPage`, currently `pages.py:145-148`):

```python
class TagIndexPage(ReservedSlugPage):
    template = "core/tag_index_page.html"
    subpage_types = ["core.TagDetailPage"]


class TagDetailPage(ModelDetailPage):
    template = "core/tag_detail_page.html"
    parent_page_types = ["core.TagIndexPage"]
    subpage_types = []

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.core.selectors import pages_tagged_with  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        context["tagged_pages"] = pages_tagged_with(self.source)
        return context
```

**Notes**
- The inline import avoids a circular import (`selectors` imports page models).
  The repo already uses `# noqa: PLC0415` for this pattern (e.g. `pages.py:58`).
- `ModelDetailPage` is already imported at `pages.py:3`.
- `self.source` is the `GenericForeignKey` to the `AllowedTag`.

---

### WP3 — Selectors (querysets + tag helpers)

**New file** `neuromancers_network/core/selectors.py` (full contents):

```python
"""Query helpers for the page-tree feeds and tag pages."""

from __future__ import annotations

from django.apps import apps
from django.conf import settings
from wagtail.models import Page

from neuromancers_network.core.models.pages import StandardPage
from neuromancers_network.core.models.pages import TagDetailPage


def _allowed_page_types():
    """Page models permitted in the generic page feeds (allowlist)."""
    paths = getattr(settings, "WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES", []) or []
    models = []
    for path in paths:
        model = apps.get_model(path)
        if model is not None:
            models.append(model)
    return tuple(models)


def _host_page(request=None, page=None):
    """Return the host page from the served page or a ``?page=`` fallback."""
    if page is not None:
        return page
    pk = (getattr(request, "GET", None) or {}).get("page") if request else None
    if pk:
        return Page.objects.filter(pk=pk).first()
    return None


def _scoped(request, page):
    """Return ``(host, queryset)`` for host-relative feeds."""
    host = _host_page(request, page)
    if host is None:
        return None, Page.objects.none()
    allowed = _allowed_page_types()
    queryset = Page.objects.live().public()
    if allowed:
        queryset = queryset.type(*allowed)
    return host, queryset


def _tag_slugs(request):
    if request is None:
        return []
    getlist = getattr(getattr(request, "GET", None), "getlist", None)
    if getlist is None:
        return []
    return [slug for slug in getlist("tags") if slug]


def _apply_tag_filter(queryset, request):
    """Filter by selected tags using a deduping ``pk__in`` subquery."""
    slugs = _tag_slugs(request)
    if not slugs:
        return queryset
    tagged = StandardPage.objects.filter(tags__slug__in=slugs).values("pk")
    return queryset.filter(pk__in=tagged)


def host_page_only(request=None, page=None):
    """The host page as a one-item queryset (used by the ``host_page`` model)."""
    host = _host_page(request, page)
    if host is None:
        return Page.objects.none()
    return Page.objects.filter(pk=host.pk)


def sitewide_pages(request=None, page=None):
    """Every eligible live, public content page across all sites."""
    allowed = _allowed_page_types()
    queryset = Page.objects.live().public()
    if allowed:
        queryset = queryset.type(*allowed)
    queryset = queryset.order_by("-first_published_at")
    return _apply_tag_filter(queryset, request)


def all_descendants(request=None, page=None):
    """Every eligible descendant of the host page (any depth)."""
    host, queryset = _scoped(request, page)
    if host is None:
        return Page.objects.none()
    queryset = queryset.descendant_of(host).order_by("-first_published_at")
    return _apply_tag_filter(queryset, request)


def immediate_children(request=None, page=None):
    """The host page's direct children."""
    host, queryset = _scoped(request, page)
    if host is None:
        return Page.objects.none()
    queryset = queryset.child_of(host).order_by("-first_published_at")
    return _apply_tag_filter(queryset, request)


def deeper_descendants(request=None, page=None):
    """Descendants of the host page excluding its immediate children."""
    host, queryset = _scoped(request, page)
    if host is None:
        return Page.objects.none()
    queryset = (
        queryset.descendant_of(host)
        .exclude(depth=host.depth + 1)
        .order_by("-first_published_at")
    )
    return _apply_tag_filter(queryset, request)


def tag_page_children(request=None, page=None):
    """Generated ``TagDetailPage`` children of the host ``TagIndexPage``."""
    host = _host_page(request, page)
    if host is None:
        return TagDetailPage.objects.none()
    return TagDetailPage.objects.live().public().child_of(host).order_by("title")


def pages_tagged_with(tag):
    """Live, public ``StandardPage``s carrying *tag* (deduped)."""
    if tag is None:
        return StandardPage.objects.none()
    return (
        StandardPage.objects.live()
        .public()
        .filter(tags=tag)
        .order_by("-first_published_at")
        .distinct()
    )


def page_tag_choices(request=None, page=None):
    """Active ``AllowedTag`` options for the feed tag UI."""
    from neuromancers_network.taxonomy.models import AllowedTag  # noqa: PLC0415

    tags = (
        AllowedTag.objects.filter(is_active=True)
        .select_related("group")
        .order_by("group__sort_order", "sort_order", "name")
    )
    options = []
    for tag in tags:
        label = f"{tag.group.name} · {tag.name}" if tag.group_id else tag.name
        options.append({"value": tag.slug, "label": label})
    return options
```

**Notes**
- `_apply_tag_filter` deliberately uses `pk__in` over tagged `StandardPage`s so it
  works on a base `Page` queryset and never produces duplicates.
- `Page.objects.live().public()`: `live()`/`public()` are `PageQuerySet` methods
  (`wagtail/query.py:315-321,408`). `descendant_of`/`child_of` likewise
  (`wagtail/query.py:25-52`).
- `type(*models)` filters by page content type (`wagtail/query.py:367`).
- All selectors accept `(request=None, page=None)` like
  `meetings/selectors.py:10-25`.

---

### WP4 — Template tags

**New file** `neuromancers_network/core/templatetags/page_feed.py`:

```python
"""Template tags for the page-tree feed template override."""

from __future__ import annotations

from django import template

from neuromancers_network.core.selectors import page_tag_choices

register = template.Library()

PAGE_FEED_MODELS = frozenset(
    {
        "page_sitewide",
        "page_all",
        "page_children",
        "page_deeper",
        "tag_page_children",
    }
)


@register.simple_tag
def is_page_feed(context_model):
    """True when *context_model* is one of the page-tree feed models."""
    return context_model in PAGE_FEED_MODELS


@register.simple_tag(takes_context=True)
def page_tag_options(context):
    """Active tag options for the feed tag UI."""
    request = context.get("request")
    page = context.get("host_page") or context.get("page")
    return page_tag_choices(request, page)


@register.simple_tag(takes_context=True)
def page_tag_selected(context):
    """Slugs currently selected in the tag filter."""
    request = context.get("request")
    getlist = getattr(getattr(request, "GET", None), "getlist", None)
    return getlist("tags") if getlist is not None else []
```

`neuromancers_network/core/templatetags/__init__.py` already exists; do not modify.

---

### WP5 — Settings

**Edit** `config/settings/base.py`.

#### 5.1 Allowlist (place near the daisIE section, before the context models)

```python
# Content page types allowed in the generic page-tree feeds. Forms, indexes,
# detail pages and system pages are implicitly excluded by this allowlist.
WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = [
    "core.StandardPage",
]
```

#### 5.2 Shared filter config + new context models

Immediately **before** `WAGTAIL_DAISIE_CONTEXT_MODELS = {` (currently
`base.py:490`), insert:

```python
_PAGE_FEED_FILTERS = {
    "search": {
        "type": "search",
        "field": "title",
        "fields": ["title", "search_description"],
        "label": "Search",
    },
    "published": {
        "type": "date_range",
        "field": "first_published_at",
        "label": "Published",
    },
}
```

Then add these entries **inside** `WAGTAIL_DAISIE_CONTEXT_MODELS` (e.g. after the
`"notification_preference"` entry, `base.py:545-549`):

```python
    "tag": {
        "label": _("Tag"),
        "model": "taxonomy.AllowedTag",
        "source": "url",
        "lookup_field": "slug",
        "lookup_in": "path",
    },
    "host_page": {
        "label": _("Current page"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.host_page_only",
    },
    "page_sitewide": {
        "label": _("Every page"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.sitewide_pages",
        "filters": _PAGE_FEED_FILTERS,
    },
    "page_all": {
        "label": _("All descendants"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.all_descendants",
        "filters": _PAGE_FEED_FILTERS,
    },
    "page_children": {
        "label": _("Child pages"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.immediate_children",
        "filters": _PAGE_FEED_FILTERS,
    },
    "page_deeper": {
        "label": _("Deeper pages"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.deeper_descendants",
        "filters": _PAGE_FEED_FILTERS,
    },
    "tag_page_children": {
        "label": _("Tag pages"),
        "model": "core.TagDetailPage",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.tag_page_children",
        "filters": _PAGE_FEED_FILTERS,
    },
```

**Notes**
- Filter labels are intentionally plain `str` (not `gettext_lazy`) so they stay
  JSON-safe for the admin (`base.py:595-596`).
- `_PAGE_FEED_FILTERS` is shared by reference; daisIE copies filter specs during
  normalisation, so sharing is safe.
- There is deliberately **no `tags` filter** (see §2.4).

#### 5.3 Detail-page config for tags

Add a `"tag"` entry to `WAGTAIL_DAISIE_DETAIL_PAGES` (`base.py:712-761`):

```python
    "tag": {
        "label": "Tag",
        "model": "taxonomy.AllowedTag",
        "page_type": "neuromancers_network.core.models.pages.TagDetailPage",
        "parent": "neuromancers_network.core.models.pages.TagIndexPage",
        "template_page": "neuromancers_network.core.models.pages.TagIndexPage",
        "lookup_field": "slug",
        "lookup_in": "path",
        "publish_field": "is_active",
        "title_source": "name",
        "slug_source": "slug",
        "on_delete": "page",
    },
```

---

### WP6 — Feed template override (option B)

**New file**
`neuromancers_network/templates/wagtail_daisIE/blocks/data/feed.html`.

This is the stock daisIE template plus guarded additions. Use exactly this
content:

```html
{% load static i18n page_feed %}
{% is_page_feed value.feed.context_model as page_feed %}
{% if audience_allowed %}
  {% page_tag_options as tag_options %}
  {% page_tag_selected as selected_tags %}
  <div
    class="{% if block_css %}{{ block_css }}{% endif %}"{% if block_style %} style="{{ block_style }}"{% endif %}
    data-daisie-feed
    data-url="{{ feed_url }}{% if page_feed %}?page={{ host_page.pk }}{% endif %}"
    data-offset="{{ next_offset }}"
    data-infinite="{% if value.feed.infinite %}true{% else %}false{% endif %}"
  >
    {% if filters or tag_options and page_feed %}
      <form method="get" class="mb-6 space-y-4" data-daisie-feed-form>
        {% if page_feed and host_page %}
          <input type="hidden" name="page" value="{{ host_page.pk }}" />
        {% endif %}
        {% if page_feed and tag_options %}
          <fieldset class="fieldset">
            <legend class="fieldset-legend">{% trans "Categories" %}</legend>
            <div class="flex flex-wrap gap-2">
              {% for option in tag_options %}
                <label class="btn btn-sm{% if option.value in selected_tags %} btn-active{% endif %}">
                  <input
                    type="checkbox"
                    name="tags"
                    value="{{ option.value }}"
                    class="sr-only"
                    {% if option.value in selected_tags %}checked{% endif %}
                  />
                  {{ option.label }}
                </label>
              {% endfor %}
            </div>
          </fieldset>
        {% endif %}
        {% for filter in filters %}
          {% include "wagtail_daisIE/blocks/data/feed_filter.html" with filter=filter %}
        {% endfor %}
        <noscript>
          <button type="submit" class="{{ submit_css }}">{% trans "Apply" %}</button>
        </noscript>
      </form>
    {% endif %}

    {% if allow_layout_toggle and toggle_options %}
      <div class="mb-4 flex justify-end" data-daisie-feed-toggle hidden>
        <div class="join" role="radiogroup" aria-label="{% trans 'Layout' %}">
          {% for option in toggle_options %}
            <label class="btn btn-sm join-item{% if option.value == layout %} btn-active{% endif %}">
              <input type="radio" name="feed_layout" value="{{ option.value }}"
                     class="sr-only"{% if option.value == layout %} checked{% endif %}
                     data-daisie-feed-layout-option />
              {{ option.label }}
            </label>
          {% endfor %}
        </div>
      </div>
      {{ layout_classes|json_script:"daisie-feed-layout-classes" }}
    {% endif %}

    <div
      data-daisie-feed-items
      data-daisie-feed-layout="{{ layout }}"
      class="{{ layout_container_css }}"
    >{{ items_html|safe }}</div>

    {% if not items_html %}
      <p class="text-base-content/70">{{ value.feed.empty_message }}</p>
    {% endif %}

    <p class="mt-3 text-sm" role="status" aria-live="polite" data-daisie-feed-status></p>

    {% if has_more %}
      <div class="mt-4 text-center">
        <a
          href="{% if page_feed %}{% querystring offset=next_offset page=host_page.pk %}{% else %}?offset={{ next_offset }}{% endif %}"
          class="{{ submit_css }}"
          data-daisie-feed-more
        >
          {% trans "Load more" %}
        </a>
      </div>
    {% endif %}

    <script src="{% static 'wagtail_daisIE/js/feed.js' %}" defer></script>
  </div>
{% endif %}
```

**Notes**
- `{% querystring %}` is built into Django ≥5.1 (this project is Django 6.0) and
  preserves existing `tags`/`search`/date params on the "Load more" link.
- `host_page` reaches the block context because it is a configured context model
  (`dynamic/context.py:27`).
- The override only injects `page`/tag UI for the whitelisted feed context models
  via `is_page_feed`, so other feeds (e.g. meetings) are unaffected.
- `{% load page_feed %}` refers to `core/templatetags/page_feed.py`.

---

### WP7 — Tag page templates

**New file** `neuromancers_network/core/templates/core/tag_index_page.html`:

```html
{% extends "base.html" %}

{% load wagtailcore_tags %}

{% block title %}
  {% if page.seo_title %}
    {{ page.seo_title }}
  {% else %}
    {{ page.title }}
  {% endif %}
{% endblock title %}
{% block content %}
  <section class="mx-auto max-w-5xl py-8">
    <h1 class="text-4xl font-bold">{{ page.title }}</h1>
    {% for block in page.body %}
      {% include_block block %}
    {% endfor %}
  </section>
{% endblock content %}
```

**New file** `neuromancers_network/core/templates/core/tag_detail_page.html`:

```html
{% extends "base.html" %}

{% load wagtailcore_tags %}

{% block title %}
  {% if page.seo_title %}
    {{ page.seo_title }}
  {% else %}
    {{ page.title }}
  {% endif %}
{% endblock title %}
{% block content %}
  <article class="mx-auto max-w-3xl py-8">
    <h1 class="text-4xl font-bold">{{ tag.name|default:page.title }}</h1>
    {% if tag.description %}
      <p class="mt-4 text-lg text-base-content/80">{{ tag.description }}</p>
    {% endif %}
    {% for block in page.body %}
      {% include_block block %}
    {% endfor %}
    {% if tagged_pages %}
      <ul class="mt-8 space-y-3">
        {% for item in tagged_pages %}
          <li>
            <a class="link link-hover text-lg" href="{{ item.url }}">{{ item.title }}</a>
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <p class="mt-8 text-base-content/70">No pages have this tag yet.</p>
    {% endif %}
  </article>
{% endblock content %}
```

The `tag` variable resolves automatically from the `tag` context model
(`source: "url"`, `lookup_field: "slug"`) using the path slug published by
`ModelDetailPage.get_context` (`detail_pages/models.py:131-135`).

---

### WP8 — Migration

Run:

```bash
just manage makemigrations core
just manage migrate
```

Expected new migration: `neuromancers_network/core/migrations/0004_*.py`
(through-model `StandardPageTag`, `StandardPage.tags` M2M, and the two new page
models `TagIndexPage` / `TagDetailPage`). Commit it.

---

### WP9 — Tests

**New file** `neuromancers_network/core/tests/test_page_feeds.py`:

```python
from __future__ import annotations

import pytest
from django.test import RequestFactory
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.core.selectors import all_descendants
from neuromancers_network.core.selectors import immediate_children
from neuromancers_network.core.selectors import sitewide_pages
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def home() -> HomePage:
    page = HomePage.objects.first()
    if page is None:
        root = Page.get_first_root_node()
        page = HomePage(title="Home", slug="home")
        root.add_child(instance=page)
    return page


def _add(parent, title, slug, tags=(), live=True) -> StandardPage:
    page = StandardPage(title=title, slug=slug)
    parent.add_child(instance=page)
    if live:
        page.save_revision().publish()
    for tag in tags:
        page.tags.add(tag)
    return page


def _request(**params):
    return RequestFactory().get("/", params)


class TestPageScopes:
    def test_immediate_children_only(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        child = _add(home, "Child", "child")
        grandchild = _add(child, "Grandchild", "grandchild")

        titles = {p.title for p in immediate_children(page=home)}
        assert titles == {"Child"}
        assert grandchild.title not in titles

    def test_all_descendants_includes_children_and_deeper(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        child = _add(home, "Child", "child")
        _add(child, "Grandchild", "grandchild")

        titles = {p.title for p in all_descendants(page=home)}
        assert titles == {"Child", "Grandchild"}

    def test_sitewide_pages_are_live_and_public(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        live = _add(home, "Live", "live")
        _add(home, "Draft", "draft", live=False)

        titles = {p.title for p in sitewide_pages()}
        assert live.title in titles
        assert "Draft" not in titles


class TestTagFiltering:
    def test_multi_tag_filter_is_deduped(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        tag_a = AllowedTagFactory(name="alpha")
        tag_b = AllowedTagFactory(name="beta")
        both = _add(home, "Both", "both", tags=(tag_a, tag_b))

        request = _request(tags=[tag_a.slug, tag_b.slug])
        results = list(sitewide_pages(request=request))

        assert [p.pk for p in results] == [both.pk]

    def test_host_page_fallback_from_query_string(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        child = _add(home, "Child", "child")

        results = list(all_descendants(request=_request(page=home.pk)))
        assert [p.pk for p in results] == [child.pk]
```

**New file** `neuromancers_network/core/tests/test_tag_pages.py`:

```python
from __future__ import annotations

import pytest
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.core.models.pages import TagDetailPage
from neuromancers_network.core.models.pages import TagIndexPage
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tag_index() -> TagIndexPage:
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)
    index = home.get_children().filter(slug="tags").first()
    if index is None:
        index = TagIndexPage(title="Tags", slug="tags")
        home.add_child(instance=index)
        index.save_revision().publish()
    return index.specific


class TestTagDetailPages:
    def test_page_created_for_active_tag(self, tag_index):
        tag = AllowedTagFactory(name="anxiety", is_active=True)

        page = TagDetailPage.objects.filter(
            detail_key="tag", source_object_id=tag.pk
        ).first()

        assert page is not None
        assert page.live is True
        assert page.title == "anxiety"

    def test_page_deleted_with_tag(self, tag_index):
        tag = AllowedTagFactory(name="grief")
        assert TagDetailPage.objects.filter(source_object_id=tag.pk).exists()

        tag.delete()

        assert not TagDetailPage.objects.filter(source_object_id=tag.pk).exists()


class TestTagDetailContext:
    def test_tagged_pages_lists_pages_with_tag(self, tag_index):
        tag = AllowedTagFactory(name="focus")
        index = Page.objects.get(pk=tag_index.pk)
        page = StandardPage(title="Tagged", slug="tagged")
        index.add_child(instance=page)
        page.save_revision().publish()
        page.tags.add(tag)

        detail = TagDetailPage.objects.get(source_object_id=tag.pk)
        context = detail.get_context(_request())

        titles = {p.title for p in context["tagged_pages"]}
        assert "Tagged" in titles


def _request():
    from django.test import RequestFactory

    return RequestFactory().get("/")
```

**Notes**
- Tests assume the seed migration created a `HomePage`; the fixtures also create
  one defensively.
- `AllowedTagFactory` lives at `neuromancers_network/taxonomy/tests/factories.py:16`.
- The signal-driven page creation requires a live `TagIndexPage` (the fixture
  ensures one).

---

### WP10 — Admin configuration (manual, no code)

After migrating, in the Wagtail admin:

1. **Create a Tag index page**: under Home, add a `TagIndexPage` (e.g. slug
   `tags`). Optionally add a `tag_page_children` **Feed** block to its body to list
   tag pages.
2. **Create 4 Feed snippets** (Snippets → Feeds) using these context models:
   `page_sitewide`, `page_all`, `page_children`, `page_deeper`. For each:
   - set an order (e.g. `-first_published_at`),
   - set page size, layout, item card blocks (e.g. title link, summary),
   - enable the `search` and `published` filters.
3. **Create a Feed snippet** for `tag_page_children` (used on the tag index page).
4. **Tag content pages**: edit a `StandardPage` and set Categories (AllowedTags).
5. Insert the relevant **Feed** blocks into `StandardPage` bodies.

The tag multi-select appears automatically on each page-tree feed (rendered by
the template override); no Feed-snippet config is needed for tags.

---

## 4. Verification

Run all of the following and confirm success:

```bash
just manage makemigrations core      # emits 0004_*; then commit it
just manage migrate                  # applies cleanly
just pytest core/tests/test_page_feeds.py core/tests/test_tag_pages.py
just pytest                          # full suite still green
just lint                            # ruff/format/djlint/stylelint
```

Manual smoke test (optional, using the dev server):

1. Run `just manage runserver` (or the compose dev service).
2. Create a `TagIndexPage` and an `AllowedTag` in the admin; confirm a
   `TagDetailPage` is generated under it and is live when the tag is active.
3. Create the feeds and place them on pages; confirm:
   - the four scopes return the expected pages,
   - tag checkboxes filter results with **no duplicate cards**,
   - "Load more" preserves active filters (Django `{% querystring %}`),
   - pagination counts are correct.

---

## 5. Acceptance criteria

- [ ] `StandardPage` exposes a `tags` field in the admin, restricted to
      `taxonomy.AllowedTag`.
- [ ] Four page-tree feed context models exist and return the correct scopes:
      site-wide, all descendants, immediate children, deeper (grandchildren+).
- [ ] Generic page feeds contain only `StandardPage` content (the allowlist),
      excluding forms/index/detail/system pages.
- [ ] Multi-select tag filtering returns each page **at most once**, with correct
      pagination totals.
- [ ] The tag UI appears only on the whitelisted page feeds; other feeds are
      unaffected by the template override.
- [ ] Every `AllowedTag` gets a generated `TagDetailPage` under the tag index;
      deleting a tag deletes its page.
- [ ] `TagDetailPage` lists the pages carrying its tag.
- [ ] `just pytest` and `just lint` pass.

---

## 6. Known limitations & caveats

1. **Taggit is not revisioned.** Tags on a page save to the live page, not to a
   draft revision. Accepted.
2. **`publish_field: "is_active"` does not unpublish.** daisIE's
   `sync_detail_page` publishes when the field is truthy but, when falsy, only
   creates a draft revision — it does **not** unpublish an already-live page
   (`detail_pages/bridges.py:94-101`). Deactivating a tag therefore leaves its
   page live until manually unpublished. If true unpublish-on-deactivate is
   required, add a small project `post_save` receiver on `AllowedTag` that
   unpublishes the linked page; this is out of scope for the base implementation.
3. **All `AllowedTag`s get a detail page**, including unused/empty tags (product
   decision). Inactive tags may still show as live pages per caveat 2.
4. **Template override is global** (it replaces the daisIE feed template for every
   feed) but is guarded by `is_page_feed`, so only the whitelisted context models
   receive the `page` param and tag UI.
5. **AJAX endpoint has no `page` argument.** The `?page=` fallback in
   `_host_page` covers this. Today `wagtail_daisIE/js/feed.js` is not shipped, so
   pagination/filters degrade to full-page GETs; `{% querystring %}` keeps filters
   on "Load more". If `feed.js` is later bundled, the `data-url` already carries
   `?page=`.
6. **Item cards use base `Page` instances.** Fields available are base page fields
   (`title`, `url`, `search_description`, dates). For StandardPage-specific data
   (e.g. `body`, `tags`) call `.specific()` in the selector or use a template tag;
   not included by default to avoid N+1 queries.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `FieldError: Cannot resolve keyword 'tags'` | Filtering a base `Page` queryset directly by `tags` | Use `_apply_tag_filter` (the `pk__in` subquery) — never `filter(tags__...)` on a base `Page` queryset. |
| Duplicate feed cards | Declared a `tags` filter in settings | Remove the `tags` filter from `_PAGE_FEED_FILTERS`; tag filtering is selector-side only. |
| Tag filter ignored on "Load more" | Active params dropped | Ensure the load-more link uses `{% querystring offset=next_offset page=host_page.pk %}`. |
| `host_page` empty in template | `host_page` not a configured context model, or not present in parent context | Confirm the `host_page` entry in `WAGTAIL_DAISIE_CONTEXT_MODELS` and that `copy_context_values` runs. |
| No `TagDetailPage` generated | No live `TagIndexPage`, or signals not connected | Create/publish a `TagIndexPage`; confirm `WAGTAIL_DAISIE_DETAIL_PAGES["tag"]` and daisIE `AppConfig.ready` ran. |
| Other feeds get a `?page=` param | Guard missing/incorrect | Verify `is_page_feed` and the `PAGE_FEED_MODELS` set in `core/templatetags/page_feed.py`. |
| Circular import on boot | `selectors` imported at module top of `pages.py` | Keep the `pages_tagged_with` import **inside** `TagDetailPage.get_context` (with `# noqa: PLC0415`). |

---

## 8. File manifest

New:
- `neuromancers_network/core/models/tag.py`
- `neuromancers_network/core/selectors.py`
- `neuromancers_network/core/templatetags/page_feed.py`
- `neuromancers_network/templates/wagtail_daisIE/blocks/data/feed.html`
- `neuromancers_network/core/templates/core/tag_index_page.html`
- `neuromancers_network/core/templates/core/tag_detail_page.html`
- `neuromancers_network/core/migrations/0004_*.py` (generated)
- `neuromancers_network/core/tests/test_page_feeds.py`
- `neuromancers_network/core/tests/test_tag_pages.py`

Modified:
- `neuromancers_network/core/models/pages.py`
- `config/settings/base.py`
