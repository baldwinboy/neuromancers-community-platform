# daisIE integration

`wagtail-daisIE` supplies the design system and dynamic content layer. The
project extends it through settings and a few code-owned hooks; UI is otherwise
authored in Wagtail.

## Page and block model

- Project pages subclass `StyledPageMixin` (via `core.models.pages`) and expose
  a `body` StreamField of daisIE content blocks.
- `core/page_blocks.py` registers project-contributed blocks
  (`metric_chart`, `cookie_registry`) by appending to
  `ALL_CONTENT_BLOCKS`/`PAGE_CONTENT_BLOCKS`. This runs from
  `core/models/__init__.py` **before** `wagtail_daisIE.pages` is imported,
  because daisIE snapshots its block list earlier than local apps load. Calling
  `register_content_block` from an app's `apps.py` is too early (translations)
  and from models is too late (the list is already built).
- Block changes alter every page/form StreamField; regenerate migrations for the
  apps that own those fields (`core`, `peers`, `meetings`, `moderation`, `users`).

## Dynamic content

- **Context models** (`WAGTAIL_DAISIE_CONTEXT_MODELS`, `config/settings/base.py`)
  expose selectors such as `viewable_bookings`, `my_meetings`,
  `my_reviews` to admin-authored blocks/feeds.
- **Detail pages** (`WAGTAIL_DAISIE_DETAIL_PAGES`) generate pages from models.
  Project subclasses resolve their own source (`SourceBoundDetailPage`) and
  delete pages with their source (`on_delete: "page"`).
- **Feeds** use viewer-scoped selectors; model feeds retain the host page across
  AJAX via the hidden `page` input.
- **Actions** are registered in `WAGTAIL_DAISIE_ACTIONS` and authorise inside
  their handlers (e.g. `review.approve`, `review.hide`).
- **Audience rules** (`WAGTAIL_DAISIE_AUDIENCE_RULES`) gate content and scripts;
  rules may combine with OR semantics.
- **Form pages** (`DaisieFormPage`) map admin-authored fields to model fields
  (`SupportFormPage`, `ReviewFormPage`).
- **Notification bridges** map inbox events to admin-authored daisIE email
  templates (`WAGTAIL_DAISIE_NOTIFICATION_BRIDGES`).

## Templates

Project overrides live under `neuromancers_network/templates/` (for example
`wagtail_daisIE/blocks/data/feed.html` — the hidden page scope input) and
`core/templates/`. Prefer overriding or extending daisIE templates over copying
large block trees.

## Version and migrations

The project pins `wagtail-daisIE==3.5.0`. That release serialises blocks by
registry key rather than a frozen tree; existing data is unchanged, but new
block additions still require `makemigrations` for the affected apps. See the
[upstream docs](https://github.com/baldwinboy/wagtail-daisIE) for details.
