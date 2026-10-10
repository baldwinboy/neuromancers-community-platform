# Settings Page Roadmap

Recreate the tabbed **Settings** page from the old `mvp` branch on the current
`core.SettingsPage`, using `wagtail-daisIE` blocks for the shell and **app-owned
forms** for the mini-forms.

The end state: **admins only place blocks** (a `TabsBlock` plus one
`ActionFormBlock` per section). All markup, validation and uploads live in
`neuromancers_network`, loaded into the tabs with htmx.

- No new pages, models, or migrations: the existing `core.SettingsPage`
  (`neuromancers_network/core/models/pages.py`) is reused.
- Progressive enhancement: every form still works without JavaScript (full
  POST + `{% daisie_messages %}`).
- The app owns forms; `wagtail-daisIE` owns the tab shell, icons, audience
  gating, `?tab=` state and the block palette.

---

## Architecture

```
SettingsPage.body
└── TabsBlock                         (admin-authored, daisIE)
    ├── TabItemBlock key=account   icon=…            audience=…
    │   └── ActionFormBlock action="settings.account"
    ├── TabItemBlock key=profile   icon=…            audience=…
    │   └── ActionFormBlock action="settings.profile"
    ├── TabItemBlock key=notifications               audience=…
    │   └── ActionFormBlock action="settings.notifications"
    ├── TabItemBlock key=calendar                    audience=…
    │   └── ActionFormBlock action="settings.calendar"
    ├── TabItemBlock key=privacy   audience=peer
    │   └── ActionFormBlock action="settings.privacy"
    └── TabItemBlock key=payments  audience=peer
        └── ActionFormBlock action="settings.payments"
```

`ActionFormBlock` normally collects daisie input blocks; the app overrides its
template so that, for the reserved `settings.*` action keys, it instead loads a
full app-rendered form:

```
GET  /settings/forms/<key>/   -> fragment with current values  (prefill)
POST /settings/forms/<key>/   -> fragment with errors/success  (validation, upload)
```

`TabsBlock`/`TabItemBlock` continue to provide the tab strip, icons, audience
gating and `?tab=` selection (no app code needed for that).

---

## B1. Prerequisites

1. Release `wagtail-daisIE` containing the new features (`TabsBlock` icons /
   `key` / per-tab `audience` / wider tab content, `ActionFormBlock`, htmx).
2. Bump the pin in `pyproject.toml` (`wagtail-daisie==X.Y.Z`) and run
   `uv sync`.
3. Confirm `django_htmx` wiring is present in `config/settings/base.py`:
   - `"django_htmx"` in `INSTALLED_APPS`
   - `"django_htmx.middleware.HtmxMiddleware"` in `MIDDLEWARE`
   - `WAGTAIL_DAISIE_HTMX = True`, `WAGTAIL_DAISIE_HTMX_VERSION = 2`
4. ~~Uncomment `{% daisie_htmx %}` in
   `neuromancers_network/templates/base.html`~~
   **Done** — `wagtail-daisIE 3.1.0` ships the tag; it now loads htmx 2 and
   `django-htmx` (settings + middleware already satisfy the `W001`/`W002` checks).
```sh
uv sync
uv run ./manage.py check          # should be warning-free for wagtail_daisIE.W001/W002
uv run ./manage.py migrate
```

---

## B2. App-owned forms

Create a `settings` package under the users app:

```
neuromancers_network/users/settings/
├── __init__.py
├── forms.py
├── registry.py
├── views.py
├── urls.py
└── templates/users/settings/
    ├── _section.html          # form wrapper + errors + submit
    ├── _account.html
    ├── _profile.html
    ├── _notifications.html
    ├── _privacy.html
    ├── _payments.html
    └── _calendar.html
```

Adapt the `mvp` forms (`mvp:apps/accounts/forms.py`) to the **current** models:

| mvp form | current model(s) |
|---|---|
| `AccountSettingsForm` | `users.User` (`first_name`, `last_name`, `username`, `date_of_birth`) |
| `ProfileForm` | `users.UserProfile` (`access_needs`, `access_needs_visible_to_peer`, `visibility`, `country`, `timezone`, `languages`, `profile_picture_url`) |
| `NotificationSettingsForm` | `users.UserProfile.notify_*` + `inbox.NotificationPreference.disabled_event_types` |
| `PeerPrivacySettingsForm` | `users.UserProfile.visibility` / `access_needs_visible_to_peer` |

Move the mvp validators (`name_no_banned_words`, `name_safe_characters`,
`user_over_18`, username uniqueness) into the app (they already exist in
`users/validators.py`).

```python
# neuromancers_network/users/settings/forms.py
from django import forms
from django.contrib.auth import get_user_model
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.validators import validate_username_not_blocked

User = get_user_model()


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "date_of_birth")
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}

    def clean_username(self):
        value = self.cleaned_data["username"].lower()
        if User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with that username already exists.")
        validate_username_not_blocked(value)
        return value


class ProfileForm(forms.ModelForm):
    display_picture_file = forms.FileField(required=False, label="Profile picture")

    class Meta:
        model = UserProfile
        fields = ("access_needs", "country", "timezone", "languages")
```

> Keep the current join/save helpers (`core/actions.py`) where practical; the
> forms only need to expose `initial` and validate.

---

## B3. Section registry

One place maps an action key to its form, save logic and permission:

```python
# neuromancers_network/users/settings/registry.py
from dataclasses import dataclass
from collections.abc import Callable

from . import forms


@dataclass(frozen=True)
class Section:
    key: str  # "settings.account"
    form: type
    save: Callable  # (request, form) -> None
    audience: str = "authenticated"  # informational; tab gating uses blocks


def _save_account(request, form):
    form.save()


def _save_profile(request, form):
    profile = form.save(commit=False)
    handle_avatar(request, profile)  # see B8
    profile.save()
    form.save_m2m()


SECTIONS: dict[str, Section] = {
    "settings.account": Section("settings.account", forms.AccountForm, _save_account),
    "settings.profile": Section("settings.profile", forms.ProfileForm, _save_profile),
    "settings.notifications": Section(
        "settings.notifications", forms.NotificationForm, ...
    ),
    "settings.privacy": Section("settings.privacy", forms.PrivacyForm, ...),
    "settings.payments": Section("settings.payments", forms.PaymentsForm, ...),
    "settings.calendar": Section("settings.calendar", forms.CalendarForm, ...),
}
```

Keys must start with `settings.` so the slot override (B6) can recognise them.

---

## B4. Section view

A single view renders and saves every section.

```python
# neuromancers_network/users/settings/views.py
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

from neuromancers_network.core.actions import redirect_back, require_authenticated
from .registry import SECTIONS


def settings_section(request, key):
    user = require_authenticated(request)
    section = SECTIONS.get(key)
    if section is None:
        from django.http import Http404

        raise Http404

    if request.method == "POST":
        form = section.form(
            request.POST, request.FILES, instance=_instance(section, user)
        )
        if form.is_valid():
            section.save(request, form)
            if getattr(request, "htmx", False):
                return HttpResponse(
                    render_to_string(_template(section), {"saved": True}, request)
                )
            messages.success(request, "Settings updated")
            return redirect_back(request)
        status = 200  # htmx swaps 2xx by default
    else:
        form = section.form(
            instance=_instance(section, user)
        )  # prefill via initial/instance
        status = 200

    html = render_to_string(
        "users/settings/_section.html",
        {"form": form, "key": key, "section": section},
        request,
    )
    return HttpResponse(html, status=status)
```

- `_instance(section, user)` returns the model instance (`user`, `user.user_profile`,
  `user.notification_preference`, …), so **GET prefills** the fields and
  **POST validates** them.
- `_template(section)` picks the per-section partial (or a shared
  `_section.html` with `{% include section.template %}`) so `payments` and
  `calendar` can render links-only panels.
- htmx requests return a fragment; non-htmx POSTs redirect with messages
  (no-JS fallback).

Wire `request.htmx` defensively if `django_htmx` is not installed:
`getattr(request, "htmx", False)`.

---

## B5. URL routing

Expose the sections before the Wagtail catch-all.

```python
# neuromancers_network/users/settings/urls.py
from django.urls import path
from .views import settings_section

app_name = "settings"

urlpatterns = [
    path("<str:key>/", settings_section, name="section"),
]
```

```python
# config/urls.py  (before the Wagtail Page catch-all)
(path("settings/forms/", include("neuromancers_network.users.settings.urls")),)
```

---

## B6. Action-form slot override

Override the plugin template so `ActionFormBlock` becomes an htmx loader for
`settings.*` keys and falls back to the plugin markup otherwise.

```django
{# neuromancers_network/templates/wagtail_daisIE/blocks/data/action_form.html #}
{% load wagtailcore_tags %}
{% if value.action|slice:":9" == "settings." %}
  <div
    hx-get="{% url 'settings:section' key=value.action %}"
    hx-trigger="load"
    hx-swap="innerHTML"
  >
    <a href="{% url 'settings:section' key=value.action %}">Open settings</a>
    <span class="loading loading-spinner"></span>
  </div>
{% else %}
  {# Keep the plugin's original action-form body here if it is used elsewhere. #}
  {% include "users/settings/_action_form_inner.html" %}
{% endif %}
```

- The app template dir already takes precedence over the package
  (`TEMPLATES.DIRS`), matching the existing `.../blocks/data/feed.html` override.
- Copy the plugin's `action_form.html` body into
  `users/settings/_action_form_inner.html` and include it in the `{% else %}`
  branch only if `ActionFormBlock` is used for non-settings actions; otherwise
  that branch can render nothing.

---

## B7. Author the page (admin only)

1. In the Wagtail admin, open the existing **Settings** page
   (`core.SettingsPage`).
2. Add a **Tabs** block.
3. For each tab set **Label**, **Key** (`account`, `profile`, `notifications`,
   `calendar`, `privacy`, `payments`), **Icon**, and — for Privacy and
   Payments — **Audience → Care providers**.
4. Inside each tab place one **Action form** block and choose the matching
   action (`settings.account`, …). Leave its fields/button empty; the app
   renders them.
5. Publish.

No migration is produced: `TabsBlock`, `TabItemBlock` and `ActionFormBlock` are
serialised by registry key, and the page/body streams are unchanged.

---

## B8. Profile avatar pipeline

`ProfileForm.display_picture_file` is handled in the section view / save:

1. Validate content type (`image/jpeg|png|gif|webp`) and size (≤ 2 MB).
2. Compress (e.g. WebP, max dimension 512) and upload with the vendored
   GetPronto client (`core/apis.configure_getpronto()`,
   `getpronto.client.upload_presign`/`upload_confirm`).
3. Delete the previous file (`profile_picture_getpronto_id`) when replacing.
4. Store `profile_picture_url` and `profile_picture_getpronto_id` on
   `UserProfile`.
5. Render the preview in `users/settings/_profile.html`.

Because the app owns the form, the upload needs no plugin upload handler —
`request.FILES` reaches the app view directly.

---

## B9. Payments / Stripe section

- The Payments panel renders one of three states from the user's Stripe
  account (`payments.services.ensure_stripe_account` / `payment_profile`):
  connected, onboarding incomplete, or not connected.
- Reuse the existing actions/views:
  - `peer.connect_stripe` (`neuromancers_network/peers/actions.py`)
  - `peer.open_stripe_dashboard`
- Add a disconnect handler + register it in `WAGTAIL_DAISIE_ACTIONS`
  (`config/settings/base.py`), e.g. `settings.stripe_disconnect`, and render
  the button in `_payments.html` as an `ActionFormBlock`/`ActionBlock` or a
  plain POST form inside the app panel.

---

## B10. Calendar section

- Render the member's read-only ICS feed link from
  `core.models.CalendarFeedToken` (create it lazily if missing):

```python
token, _ = CalendarFeedToken.objects.get_or_create(user=user)
url = reverse("calendar_feed", kwargs={"token": token.token})
```

- Show the service information (Google/Outlook/Apple) as static content in
  `_calendar.html`. The `CalendarFeedView` already serves the file.

---

## Verification

- **Unit/functional:** GET prefill renders current values; invalid POST returns
  the fragment with field errors; valid POST persists and (htmx) returns a
  success alert; avatar upload stores the URL and deletes the old file.
- **No-JS:** with `{% daisie_htmx %}` removed/disabled, each tab's link opens
  the section URL as a full page, and POST redirects back with
  `{% daisie_messages %}`.
- **Commands:**

```sh
uv run ./manage.py check
uv run ./manage.py test users core
uv run pytest
```

- **Manual:** load `/settings` (or the page URL) and confirm tab switching,
  per-tab audience gating for non-peers, and that each mini-form saves.

---

# Peer Session Management Roadmap (list / create / edit / delete + availability)

Recreate the `mvp` PeerSession management screens on `staging` using
`wagtail-daisIE` blocks and app-owned code. **Do not change this repo until the
daisIE release below is pinned.** No new pages/models are strictly required for
the shell; the app owns forms, uploads, pricing and validation.

## Prerequisite

`wagtail-daisIE` must ship the following (see the daisIE implementation plan):

- **Autocomplete multi-select** — widget + form-field type (`choices` config
  supports `True` for the Choices box with `5-120/5` ranges, or a callable for
  model-backed options); a `Data-input` block; and a feed-filter variant
  (`autocomplete: true` on a `choice` filter).
- **`DaisieFormPage` edit mode** — `form_mode = "edit"` on a developer-defined
  page subclass; the bound instance is resolved from `context_bindings`; fields
  prefill from it and submission updates it. Class attribute only (no schema).
- **Context-bound initial/choices** — choice callables receive the bound form
  context (instance + resolved context models).
- **M2M/taggit persistence** — `create`/`update_instance_from_submission` set
  many-to-many values after save.
- **Action confirm dialog** — `ActionButtonBlock.confirm` renders a CSS `:target`
  modal; no JS/endpoint.
- **Feed `sort` filter type** and **annotation/`query` filters** in the
  context-model `filters` spec.

Bump the pin (`wagtail-daisie==X.Y.Z`), `uv sync`, then
`uv run ./manage.py check` (W001/W002 clean) and `uv run ./manage.py migrate`.

## Reuse (already present)

- Unified `meetings.Meeting` (`1:1` / `group`) with `scheduled_at` +
  `duration_minutes`; `PricingType.DURATION_TIERS`.
- `MeetingPriceTier(duration_minutes, is_default)` +
  `MeetingPriceOption(amount, label, is_default)`, consumed by
  `Meeting.price_for()` and `MeetingRequest.requested_duration_minutes`.
- `MeetingDetailPage` + `WAGTAIL_DAISIE_DETAIL_PAGES["meeting"]`.
- Existing actions: `meetings.create`, `bookings.request`.

## App-owned pieces

- `WAGTAIL_DAISIE_CONTEXT_MODELS`: add `language` (active) and `country`
  querysets for autocomplete; a `my_meeting` model (queryset filtered by
  `request.user`) for the host list.
- `WAGTAIL_DAISIE_FORM_FIELD_TYPES`:
  - `languages` / `countries` — `MultipleChoiceField` + autocomplete widget,
    `choices` callable over the taxonomy.
  - `durations` — `TypedMultipleChoiceField(coerce=int)` + autocomplete widget,
    `choices: True` (admin enters `5-120/5`).
  - `duration_tiers` — composite field + HTMX-repeater widget.
- `meetings/views.py` + `meetings/urls.py` — authenticated `GET` returning one
  `_tier_row.html` fragment for the “Add duration” button (HTMX).
- `meetings/services.py` — `sync_meeting_durations(meeting, rows)` writing
  `MeetingPriceTier` + a default `MeetingPriceOption`; `offered_durations`
  property on `Meeting`; validate `requested_duration_minutes ∈ offered_durations`.
- `Meeting.clean()` — duration tiers only valid for `1:1`.

## Admin-authored pages

1. **Host sessions** — a `Feed` (context model `my_meeting`) with item blocks:
   card + status badge + `Action` buttons **Edit / Publish / Delete** (Delete
   uses the confirm dialog). “Host a session” links to the create page.
2. **Create 1:1** — `MeetingFormPage` (page-level `meeting_type`) with
   `languages`, `countries`, `durations`, and the `duration_tiers` repeater.
3. **Edit** — `MeetingEditPage(DaisieFormPage)` (`form_mode = "edit"`) bound via
   a `context_bindings` URL `pk`; fields prefill and choices scope to the
   instance.
4. **Delete/publish** — registered actions (`meetings.delete`, `meetings.publish`)
   with a confirmation.

## Seeker scheduling (1:1)

Server-render on `MeetingDetailPage`: a duration/price **tier choice** plus a
`datetime-local` start input, posting to `bookings.request`; validate against
`offered_durations()` and reuse `MeetingRequest.clean()`’s ≥10-minute rule.
No htmx needed (the meeting is in context).

## Tests to update (app)

- `meetings/tests/test_services.py` — `create_meeting` with `durations`/languages.
- `meetings/tests/test_pricing.py` — `offered_durations` / `sync_meeting_durations`.
- `meetings/tests/test_booking.py` — reject an un-offered duration; 1:1-only tiers.

## Verification

```sh
uv run ./manage.py check
uv run ./manage.py makemigrations --check --noinput
uv run pytest
```

---

# Taxonomy Management Roadmap (tags / languages / countries)

## HTMX

- `{% daisie_htmx %}` is enabled in `base.html`; `wagtail-daisIE 3.1.0` ships the
  tag and `django_htmx` + middleware are already wired (`wagtail_daisIE.W001`/
  `W002` stay quiet).

## Admin multi-select for languages/countries

- `PeerProfileViewSet` and `MeetingViewSet` use a panel-based `edit_handler`
  (`ObjectList(..., base_form_class=...AdminForm)`) with a
  `MultiFieldPanel([FieldPanel("languages", widget=CheckboxSelectMultiple),
  FieldPanel("countries", widget=CheckboxSelectMultiple)],
  heading=..., classname="collapsed")`. The `collapsed` class renders the group
  closed by default; Wagtail's panel JS expands it automatically when a field
  has an error. Admin-only — daisIE form pages keep their own authoring blocks.
- `create_meeting()` now validates/sets `languages` (via `validate_languages`),
  and `meetings.actions` / `MeetingFormPage` route languages through it.

## Tag groups & allowed tags

- **Drill-down:** each tag group row exposes a “Manage tags” button linking to
  the tag listing filtered by that group (`?group=<pk>`); the add view is
  prefilled with the group and the listing's add URL preserves the filter. Bulk
  Activate/Deactivate run on the filtered set (Wagtail's existing bulk actions).
- **Sort order:** `TagGroup` / `AllowedTag` use a nullable `sort_order` with a
  `sort_order_field` attribute, enabling Wagtail's out-of-box drag-and-drop
  reordering (values are seeded on create because the default is `None`).
- **Slug:** both viewsets use `TitleFieldPanel("name")` so the slug mirrors the
  name while untouched. `TagGroup.slug` is now editable and only auto-filled when
  blank; `AllowedTag.slug` (taggit) is unchanged.

## Registry import (Babel / CLDR)

- `taxonomy/registry.py` loads ISO 3166-1 countries and ISO 639-1 languages from
  Babel's CLDR data, upserting by `code` and skipping name conflicts.
- Each listing (`Country`, `Language`) renders a “Load all from registry” header
  button to a confirmation view (`taxonomy/views.py`, `register_admin_urls`).
  No bulk action is registered (the header button is the single entry point and
  works on an empty listing).
