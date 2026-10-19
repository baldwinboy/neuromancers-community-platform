# Content Security Policy (deferred)

This page records the CSP design for the admin-injected scripts and daisIE
inline assets. **CSP is documented, not enforced, in the current phase.** There
is no `django-csp` dependency and no `Content-Security-Policy` header is set.

## What emits executable content today

| Source | Where | Notes |
|---|---|---|
| `ScriptsSetting` (admin-authored) | `templates/base.html` `extra_head` / `extra_body` | Raw markup, arbitrary inline or external scripts. |
| `{% daisyui_theme_script %}` | site `<head>` via daisIE | Inline script that persists the theme cookie (`daisie_theme`). |
| `{% daisie_htmx %}` | site `<head>` | htmx loader (external script plus configuration). |
| `{% daisyui_icon_assets %}` | site `<head>` | Provider scripts/styles (Iconify, webfonts, custom manifests). |
| `ArbitraryCSSMiddleware` | injected `<style>` before `</head>` | Generated rules for arbitrary colour utilities. |
| daisIE blocks | inline `style` attributes and occasional inline scripts | Design CSS is emitted inline by the block pipeline. |
| Cally calendar block | `{% daisie_cally %}` / configured CDN URL | Optional third-party calendar script. |
| Stripe Checkout | redirects to Stripe-hosted pages | No Stripe.js is embedded by this project. |

## Recommended policy (draft)

Enforce on public pages after a report-only rollout:

```text
default-src 'self';
script-src 'self' 'nonce-<per-request>' https://cdn.jsdelivr.net https://*.daily.co;
style-src 'self' 'nonce-<per-request>' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self' https://fonts.gstatic.com;
connect-src 'self' https://api.stripe.com https://api.daily.co https://api.whereby.dev;
frame-src https://*.daily.co https://*.whereby.com;
frame-ancestors 'none';
base-uri 'self';
form-action 'self' https://checkout.stripe.com;
```

Adjust the provider hosts to whichever meeting provider is configured. The
`_FRAME` directive is the enforcement counterpart to `X-Frame-Options` (see
below).

## Nonce and hash strategy

1. Add middleware that generates a fresh nonce per request
   (`secrets.token_urlsafe`), stores it on the request, and sets the CSP header.
2. Expose the nonce to templates (`request.csp_nonce`) and add `nonce="…"` to
   every inline `<script>` and `<style>`.
3. For static inline snippets, prefer SHA-256 hashes (`'sha256-…'`) over
   `'unsafe-inline'`.
4. Admin-authored scripts cannot be pre-hashed. Either:
   - require external scripts from an allowlisted host (recommended), or
   - inject the request nonce into the admin markup before rendering, or
   - accept `'unsafe-inline'` for `script-src` (not recommended; defeats CSP).
5. DaisIE template tags that emit inline scripts need either a project override
   that adds the nonce or an upstream nonce hook. Until then, CSP enforcement
   must allow their exact hashes or `'unsafe-inline'`.

### UNVERIFIED (documentation)

The exact inline snippets emitted by daisIE were not audited under CSP
enforcement. Before turning CSP on, capture the rendered HTML and classify:

- `daisyui_theme_script` (theme persistence),
- `daisie_htmx` (htmx loader/config),
- `daisyui_icon_assets` (Iconify/provider bootstrap),
- the Cally calendar loader,
- `ArbitraryCSSMiddleware`'s injected `<style>`,
- any block-level inline `style` attributes (these require `style-src
  'unsafe-inline'` or a hash/nonce strategy).

## `frame-ancestors` vs `X_FRAME_OPTIONS`

- `X_FRAME_OPTIONS = "DENY"` (current setting in
  `config/settings/base.py`) controls whether **this site** may be framed by
  another site.
- CSP `frame-ancestors` is the modern equivalent and, where both are present,
  browsers honour the CSP directive. If a page must remain embeddable, relax
  both together (`frame-ancestors 'self' <host>` and the matching
  `X_FRAME_OPTIONS`).
- `frame-src` controls which third-party frames **this site** may embed. It is
  unrelated to `X_FRAME_OPTIONS`; adding meeting-provider iframes requires the
  provider origin in `frame-src`.

## Rollout

1. Enable `Content-Security-Policy-Report-Only` with the draft policy and a
   report endpoint; collect violations for at least one full week of traffic.
2. Resolve inline-script violations by adding a nonce/hashes (or moving
   admin-authored scripts to allowlisted external sources).
3. Tighten `style-src` after auditing daisIE inline styles.
4. Enforce, keeping the report endpoint.

## Out of scope (this phase)

- No CSP middleware, header, or nonce support is implemented.
- No CSP tests are added; this is a documentation deliverable.
