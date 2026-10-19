# Scripts and cookie consent

## Script injection

`ScriptsSetting` (Wagtail settings) holds admin-authored scripts. Each entry has
a name, category (`necessary`/`analytics`/`marketing`), placement (`head`/`body`),
an optional audience (OR semantics; empty = everyone) and raw script markup.

`core/context_processors.py::site_scripts` filters entries by
`consent_allows(request, category)` and `evaluate_audience`, exposing
`head_scripts`/`body_scripts`; `templates/base.html` renders them in the
previously unused `extra_head`/`extra_body` blocks.

There is **no CSP enforcement** yet; arbitrary admin markup is trusted. See
[content security policy](../infra/content-security-policy.md) for the deferred
nonce/hash design and provider origins.

## Consent cookie

- Cookie name: `cookie_consent` (`core/consent.py`).
- Value: Django-signed JSON `{categories, version, timestamp}`; no server-side
  record.
- `necessary` always runs; `analytics`/`marketing` require explicit consent.
- `ConsentVaryMiddleware` adds `Vary: Cookie` to HTML responses so caches do not
  mix consent states.
- `ConsentSettings` holds admin-authored banner copy and `policy_version`.
  `consent_needs_update` shows the banner when the cookie is absent or its
  version differs, so bumping the version re-asks.

Endpoints (`config/urls.py`): `POST /consent/accept/` (accept or necessary-only;
category allowlist, version check, same-host return URL) and
`POST /consent/reset/` (withdraw and re-open). Both are CSRF-protected.

## Cookie registry and policy page

`core/models/cookies.py` defines `CookieCategory` and the admin-editable `Cookie`
snippet (name, provider, purpose, duration, category, active). Migration
`core/0020_seed_cookies.py` registers the cookies the site sets:
`django_language`, `daisie_theme`, `sessionid`, `csrftoken` (all necessary).

Admins author the policy page as a `StandardPage` and insert the
`cookie_registry` block (`core/page_blocks.py::CookieRegistryBlock`), which
renders active cookies grouped by category. The banner and policy page share
`CookieCategory`, so they cannot drift. No legal text is seeded.
