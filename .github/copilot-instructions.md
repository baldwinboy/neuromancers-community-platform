# NEUROMANCERS Community Platform

Production-grade Django/Wagtail CMS for peer support session scheduling with Stripe Connect payments and Whereby video conferencing.

## Project Philosophy

This is **production code for client handoff** to another development team. Code must adhere to:
- **DRY** (Don't Repeat Yourself) - Extract reusable patterns
- **KISS** (Keep It Simple, Stupid) - Favor clarity over cleverness
- **SOLID** principles - Single responsibility, open/closed, etc.
- **TDD** (Test-Driven Development) - Test business logic, not framework functionality

**Key Principle**: Remove unused code. If permission models, factories, or abstractions aren't actively used, they should be removed to reduce maintenance burden.

## Architecture Overview

**Core Stack**: Django 6.0 + Wagtail 7.3 + django-allauth 65.x + django-guardian 3.x (object-level permissions) + Stripe Connect + Whereby API

**Key Apps**:
- `apps/events/` - Session management (Peer/Group sessions with availability, booking requests, payments, reviews)
- `apps/accounts/` - Custom User model, profiles, user settings, Stripe accounts, group-based permissions (Peer, Support Seeker, Neuromancer)
- `apps/core/` - Wagtail pages (HomePage), reusable django-components (`accordion`, `hero`), notification email settings, social media settings
- `apps/blog/` - Blog index and blog pages (Wagtail)
- `apps/contact/` - Contact form with topics (Wagtail FormPage)
- `apps/common/` - Shared utilities (`getpronto.py` for image uploads, `utils.py`)

**Model Architecture**: Multi-file model organization
- Models split across subdirectories: `models_users/`, `models_pages/`, `models_sessions/`
- Main `models.py` aggregates via star imports
- `apps/accounts/models.py` imports from `models_users/user.py`, `models_users/profile.py`, `models_users/user_settings.py`
- `apps/events/models.py` imports from `models_pages/wagtail_pages.py`, `models_pages/wagtail_settings.py`, `models_sessions/peer.py`, `models_sessions/group.py`

**Wagtail Integration**: `SessionsIndexPage` is a `RoutablePage` serving dual purpose:
- CMS page with StreamField content (PeerFeedBlock, SessionFeedBlock)
- Custom routes for session CRUD:
  - `/create/` - Choose session type
  - `/create/<session_type>/` - Create peer or group session
  - `/edit/<session_type>/<uuid>/` - Edit session
  - `/availability/<uuid>/` - Manage peer session availability
  - `/availability/delete/<uuid>/` - Delete availability slot
  - `/request/schedule/<uuid>/` - Request/schedule a peer session
- Creates child pages (`PeerSessionDetailPage`, `GroupSessionDetailPage`) for SEO

**Wagtail Site Settings** (in `apps/events/models_pages/wagtail_settings.py` and `apps/core/models.py`):
- `StripeSettings` - Stripe API keys and client ID
- `WherebySettings` - Whereby API key
- `SessionFilterSettings` - Configurable session feed filters (cached 1h)
- `SocialMediaSettings` - Social media links
- `SiteLinkSettings` - Custom site URL (in core)
- `NotificationSettings` - Customizable email notification text for 11 email types (in core)

## Development Workflow

### Environment Setup
```bash
make venv                    # Create venv with uv
source .venv/neuromancers/bin/activate
cp .env.development .env     # Use development config
make fresh                   # Fresh install + migrations + superuser + default groups + publish sessions index + collectstatic + runserver
make dev                     # Subsequent runs (makemigrations + migrations + collectstatic + runserver)
```

**Default superuser**: `_neuro:_default_password` (`_default@neuromancers.org.uk`)

### Key Commands
- `make django-collectstatic` - **Required before running** - compiles Sass, loads SVG sprites via `scripts/load_icons.sh`, runs collectstatic
- `make sass-watch` - Watch Sass compilation during development
- `make django-seedusers USERS=50 GROUPS="Peer"` - Generate test users with factory-boy
- `make django-seedsessions SIZE=50` - Generate test sessions
- `make django-setupdefaultgroups` - Create UserGroup instances (Peer, Support Seeker, Neuromancer)
- `make django-publishsessionsindex` - Publish all unpublished SessionsIndexPages
- `make django-coverage` - Run tests with coverage report + HTML + XML
- `make django-coverage-badge` - Generate coverage badge SVG

### Management Commands
| App | Command | Purpose |
|-----|---------|---------|
| `accounts` | `seed_users` | Generate fake users with factory-boy |
| `events` | `seed_sessions` | Generate fake peer/group sessions |
| `events` | `publish_sessions_index` | Publish unpublished SessionsIndexPages |
| `events` | `send_session_reminders` | Send reminder notifications for upcoming sessions |
| `core` | `setup_default_groups` | Create default UserGroup instances |

### Testing Philosophy
- `make django-test` - Run test suite
- **Test business logic, not Django**: Models work if migrations run; test custom methods, permissions logic, edge cases
- **Factories for integration tests only**: `apps/accounts/factories.py`, `apps/events/factories.py` used for seeding data and testing complex interactions
- Example: `UserFactory(groups=['SupportSeeker'])` - useful for testing permission assignment, not model creation

## Code Quality Standards

### What to Remove (Production Cleanup)
1. **Unused Permission Models**: 24 `*ObjectPermission` classes exist (16 in accounts, 8 in events) - many are never queried directly, audit and remove
2. **Dead Code**: Commented code, unused imports, orphaned functions
3. **Over-abstraction**: If a pattern appears once, inline it
4. **Test Factories**: Remove factories that only test Django's built-in model functionality

### Two Component Systems

**1. django-components** (v0.148.0 with `djc-core` 1.3.0) for reusable UI:
- Uses `component_shorthand_formatter` — components are called by name directly as template tags
- Registered with `@djc.component.register("name")` decorator
- Component dirs include `templates/includes/`

```django
{# Shorthand syntax - NOT {% element %} #}
{% accordion %}...{% endaccordion %}
{% hero heading="Welcome" subheading="..." / %}
{% session_item session=session_data session_type="peer" / %}
{% peer_item peer=peer_data / %}
{% request_calendar available_slots=slots durations=durations /%}
```

Registered components:
- `apps/core/components/` - `accordion`, `hero`
- `apps/events/components/` - `session_item`, `peer_item`, `request_calendar`

**2. Wagtail Component** (`laces` package) for complex feed blocks:
- `SessionFeedBlock` and `PeerFeedBlock` in `apps/events/components/` extend `wagtail.blocks.StructBlock`
- Rendered via Wagtail's StreamField block system, not django-components

**3. django-allauth element system** for auth templates:
- `{% element panel %}`, `{% element button %}`, `{% element field %}` etc. in `templates/allauth/elements/`
- This is allauth's own template tag system, separate from django-components
- 22 element template overrides in `templates/allauth/elements/`

### Permissions with Django Guardian
Object-level permissions assigned via signals (`apps/events/signals.py`, `apps/accounts/signals.py`):

```python
@receiver(post_save, sender=PeerSession)
def set_peersession_permissions(sender, instance, created, **kwargs):
    if created:
        assign_perm('change_peersession', instance.host, instance)
        assign_perm('delete_peersession', instance.host, instance)
        assign_perm('schedule_session', instance.host, instance)
        assign_perm('view_peersession', instance.host, instance)
    if instance.is_published:
        assign_perm('view_peersession', support_seeker_group, instance)
        assign_perm('request_session', support_seeker_group, instance)
```

- Custom permission models: `PeerSessionUserObjectPermission`, `PeerSessionGroupObjectPermission`, etc.
- User mixin: `UserGroupPermissionsMixin` for group-based checks
- Check permissions: `user.has_perm('events.add_peersession')` or `get_objects_for_user(user, 'events.view_peersession')`
- Guardian anonymous user: username `"nonny"` (configured in `base.py`)
- **Audit needed**: 24 `*ObjectPermission` classes exist — many may never be queried directly

### Settings Structure
Multi-file settings in `neuromancers/settings/`:
- `base.py` - Core Django/Wagtail settings (`USE_TZ=True`, `TIME_ZONE="UTC"`, `AUTH_USER_MODEL="accounts.User"`)
- `dev.py` - Development overrides (DEBUG=True, console email, debug toolbar, insecure SECRET_KEY)
- `production.py` - Production overrides (security headers, HSTS, min password length 12)
- `countries.py`, `currencies.py`, `languages.py` - ISO data lists (imported as constants)
- `stripe_currencies.py` - Stripe-supported currencies
- `blacklist.py` - Username blacklist
- `bots.py` - Bot user agent list for production
- Control via `ENVIRONMENT` env var (`development`, `production`)

**Database**: SQLite for development (`db.sqlite3`), PostgreSQL recommended for production

## Model Overview

### accounts app
- `UserGroup` - Custom Group model with `label` field
- `User` - Custom user model (AbstractUser) with `date_of_birth`, `country`, `phone_number`, `username` (max 64, unique, validated)
- `Profile` - OneToOne to User (bio, languages, profile_image, etc.)
- `Certificate` - FK to Profile
- `StripeAccount` - OneToOne to User (stripe_user_id)
- `NotificationSettings` - Per-user notification preferences (notification channel + category enums)
- `AbstractUserSettings` - Abstract base for user settings models
- `PeerNotificationSettings`, `PeerFilterSettings`, `PeerPrivacySettings` - OneToOne to User, peer-specific settings
- 16 `*ObjectPermission` classes (8 User + 8 Group) for Guardian

### events app
- `AbstractSession`, `AbstractAvailability`, `AbstractSessionRequest`, `AbstractSessionReview` - Abstract base classes
- `PeerSession` - Peer-to-peer session (FK to User as host). Custom permissions: `request_session`, `schedule_session`
- `PeerSessionAvailability` - Time slots for peer sessions (with duration constraints 5min–1day)
- `PeerSessionRequest` - Booking request for peer session. Custom permissions: `approve_peer_request`, `withdraw_peer_request`
- `PeerScheduledSession` - Confirmed scheduled session (OneToOne to PeerSessionRequest)
- `PeerSessionReview` - Review for peer session (rating 1-5)
- `GroupSession` - Group session (FK to User as host, M2M attendees via GroupSessionRequest). Custom permission: `request_join_session`
- `GroupSessionRequest` - Join request for group session. Custom permissions: `approve_group_request`, `withdraw_group_request`
- `GroupSessionReview` - Review for group session
- `SessionsIndexPage` - RoutablePage for session browsing/CRUD
- `PeerSessionDetailPage`, `GroupSessionDetailPage` - SEO detail pages (child pages of SessionsIndexPage)
- `StripeSettings`, `WherebySettings`, `SessionFilterSettings`, `SocialMediaSettings` - Wagtail site settings
- `FilterItemBlock`, `FilterGroupBlock` - StreamField blocks for configurable filters
- 8 `*ObjectPermission` classes (4 User + 4 Group) for Guardian

## Integration Patterns

### Stripe Connect
- Host users authorize Stripe accounts via OAuth: `StripeAuthorizeView`, `StripeAuthorizeCallbackView`
- Disconnect: `StripeDisconnectView`
- Decorator: `@stripe_account_required` prevents session creation without connected account
- Application fee: 15% (`STRIPE_APPLICATION_FEE = 0.15`)
- Payment links created via `CreatePaymentLinkView` (calculates per-hour or flat rate, standard or concessionary)
- Refund handling: auto-refund or pending-approval via `RequestRefundView`, `ApproveRefundView`
- Payment history: `PaymentHistoryView` fetches Stripe details

### Whereby API
- API key in `.env`: `WHEREBY_API_KEY`
- Meeting links managed via `ManageMeetingLinkView` (generate/regenerate/remove)

### GetPronto API
- Image upload service for profile photos
- API key in `.env`: `GETPRONTO_API_KEY`
- Implementation in `apps/common/getpronto.py`

### Static Assets
- Sass source: `assets/scss/styles.scss` > compiled to `assets/css/styles.css`
- SVG sprites: `assets/icons/*.svg` > `templates/includes/sprite.svg` via `scripts/load_icons.sh`
- Heroicons available via `{% load heroicons %}` (third-party package)
- Compression: django-compressor enabled for production

## Common Gotchas

1. **Always run `make django-collectstatic`** after CSS/icon changes - compiles Sass AND generates SVG sprites, not just copying files
2. **URL routing**:
   - Django admin: `/django-admin/` (dev only)
   - Wagtail admin: `/admin/`
   - Auth: `/login/`, `/signup/` (django-allauth via catch-all URL patterns)
3. **Migrations**: Models in subdirectories still generate migrations in app's `migrations/` folder
4. **Custom User model**: `AUTH_USER_MODEL = "accounts.User"` - always import with `get_user_model()`
5. **Template caching**: `cached.Loader` enabled - restart server if template changes don't appear
6. **`{% element %}` is allauth's system**, not django-components — don't confuse the two
7. **Two component systems**: django-components (shorthand tags) vs Wagtail Component (laces, for feed blocks)
8. **`make fresh`** also runs `django-publishsessionsindex` and `django-setupdefaultgroups`

## File Patterns

- Model imports: `apps/*/models.py` imports from `models_*/`
- Management commands: `apps/*/management/commands/*.py`
- Factories: `apps/*/factories.py` (factory-boy)
- Forms: `apps/*/forms.py`, form subdirectories: `apps/events/forms_sessions/`
- Form fields: `apps/events/form_fields.py`
- Signals: `apps/*/signals.py` (auto-connected via AppConfig `ready()`)
- Wagtail hooks: `apps/*/wagtail_hooks.py`
- Template tags: `apps/*/templatetags/` (e.g., `get_item`, `getpronto`, `navigation_tags`)
- Components: `apps/*/components/` (django-components and Wagtail Components)
- Choices/enums: `apps/events/choices.py`
- Decorators: `apps/events/decorators.py` (`parse_uuid_param`, `with_route_name`, `stripe_account_required`)
- Validators: `apps/*/validators.py`
- Mixins: `apps/*/mixins.py`
- Notifications: `apps/*/notifications.py`
- Calendar export: `apps/events/calendar_export.py`

## External Dependencies

- **uv** for Python package management (not pip directly)
- **Dart Sass** for CSS compilation
- **Make** for task automation
- **pre-commit** for linting (installed via `make install`)
- Requirements: `requirements/base.in` > compile with `make update-requirements` (uses `pip-compile`) > generates `base.txt`
- Key packages: Django 6.0.2, Wagtail 7.3, django-components 0.148.0, django-guardian 3.0.3, django-allauth 65.13.0, stripe 12.3.0, heroicons 2.11.0, django-tasks 0.9.0
