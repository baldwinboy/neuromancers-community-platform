# Feature → code location

| Feature | Where |
|---|---|
| Detail pages (meeting, peer, review, profile, tag, booking, refund) | `core/models/pages.py`; `WAGTAIL_DAISIE_DETAIL_PAGES` and context models in `config/settings/base.py`; serve guard in `core/wagtail_hooks.py` |
| Owner/participant visibility and blocks | `moderation/visibility.py`; serve guard `core/wagtail_hooks.py` |
| Unified site search | `core/search_service.py`; `SearchPage` in `core/models/pages.py`; template `core/templates/core/search_results.html`; `StandardPage.search_fields` |
| Two-party feeds and selectors | `meetings/selectors.py`; context models in `config/settings/base.py`; `templates/wagtail_daisIE/blocks/data/feed.html` |
| Booking/refund participant pages | `core/models/pages.py` (`BookingDetailPage`, `RefundRequestDetailPage` and templates); `moderation/visibility.py::source_participant_ids` |
| Meeting join window and links | `meetings/join.py`; endpoint in `meetings/views.py` + `meetings/urls.py`; audience rules in `core/audience.py`; provider `join_url` in `core/meeting_providers/` |
| Checkout, pricing, refunds | `meetings/models/{meeting,request,booking,refund}.py`; `payments/charges.py`; `payments/services.py`; webhook handlers `meetings/signals.py` |
| Currency capture | `core/currency.py::base_conversion`; `MeetingRequest.sync_payment_from_checkout`; ledger writers in `analytics/services.py` |
| Review approval and peer hide | `meetings/models/review.py`; `meetings/forms_pages.py::ReviewFormPage`; `meetings/actions.py` (`review_approve`, `review_hide`); bulk actions in `meetings/wagtail_hooks.py`; notifications in `inbox/signals.py` |
| Public review/session aggregates | `meetings/selectors.py::review_stats`; injected by `MeetingDetailPage`/`PeerProfileDetailPage` in `core/models/pages.py` |
| Analytics ledgers and metrics | `analytics/models.py`, `analytics/services.py`, `analytics/metrics.py`; wiring in `meetings/signals.py`, `peers/signals.py`, `meetings/tasks.py` |
| Analytics admin/API/chart | `analytics/views.py`, `analytics/panels.py`, `analytics/wagtail_hooks.py`, `analytics/api.py`, `analytics/blocks.py`; `config/api.py` |
| Script injection | `core/models/settings.py::ScriptsSetting`; `core/context_processors.py::site_scripts`; `templates/base.html` blocks |
| Consent banner and cookie | `core/consent.py`; `core/views/consent.py`; `core/context_processors.py::consent_banner`; `core/templates/core/includes/consent_banner.html`; `core/middleware.py::ConsentVaryMiddleware` |
| Cookie registry and policy block | `core/models/cookies.py`; `core/page_blocks.py::CookieRegistryBlock`; `core/templates/core/blocks/cookie_registry.html`; seed migration `core/0020_seed_cookies.py` |
| Notifications and email bridges | `inbox/events.py`, `inbox/signals.py`, `inbox/models/`, `inbox/payloads.py`; bridges in `config/settings/base.py` |
| Moderation (bans, tickets, exports, deletion) | `moderation/` (`banning.py`, `services.py`, `export.py`, `wagtail_hooks.py`, `views.py`) |
| Admin guide content and reader | `core/help_seed.yaml`, `core/help_seed.py`, `core/views/help.py`, `core/templates/core/help_guide.html` |
| Encrypted settings fields | `core/crypto.py`, `core/fields.py`, `core/forms.py`, `core/checks.py` |
| Bootstrap and seed data | `compose/production/django/start-init`, `compose/local/django/start`; `core/management/commands/bootstrap.py` and related commands |
