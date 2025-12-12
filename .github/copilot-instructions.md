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

**Core Stack**: Django 5.2 + Wagtail CMS + django-allauth + django-guardian (object-level permissions) + Stripe Connect + Whereby API

**Key Apps**:
- `apps/events/` - Session management (Peer/Group sessions with availability, booking requests)
- `apps/accounts/` - Custom User model with group-based permissions (Peer, Support Seeker, Neuromancer)
- `apps/core/` - Wagtail pages (HomePage) and reusable django-components
- `apps/blog/`, `apps/contact/` - Standard CMS features

**Model Architecture**: Multi-file model organization
- Models split across subdirectories: `models_users/`, `models_pages/`, `models_sessions/`
- Main `models.py` aggregates via star imports: `from .models_users.user import *`
- Example: `apps/events/models.py` imports from `models_pages/wagtail_pages.py`, `models_sessions/peer.py`

**Wagtail Integration**: `SessionsIndexPage` is a `RoutablePage` serving dual purpose:
- CMS page with StreamField content
- Custom routes (`/create/`, `/peer/<uuid>/edit/`) for session CRUD operations
- Creates child pages (`PeerSessionDetailPage`, `GroupSessionDetailPage`) for SEO

## Development Workflow

### Environment Setup
```bash
make venv                    # Create venv with uv
source .venv/neuromancers/bin/activate
cp .env.development .env     # Use development config
make fresh                   # Fresh install + migrations + superuser + collectstatic + runserver
make dev                     # Subsequent runs (migrations + collectstatic + runserver)
```

**Default superuser**: `_neuro:_default_password` (configured in Makefile)

### Key Commands
- `make django-collectstatic` - **Required before running** - compiles Sass, loads SVG sprites via `scripts/load_icons.sh`, runs collectstatic
- `make sass-watch` - Watch Sass compilation during development
- `make django-seedusers USERS=50 GROUPS="Peer"` - Generate test users with factory-boy
- `make django-seedsessions SIZE=50` - Generate test sessions
- `make django-setupdefaultgroups` - Create UserGroup instances (Peer, Support Seeker, etc.)

### Testing Philosophy
- `make django-test` - Run test suite
- **Test business logic, not Django**: Models work if migrations run; test custom methods, permissions logic, edge cases
- **Factories for integration tests only**: `apps/accounts/factories.py`, `apps/events/factories.py` used for seeding data and testing complex interactions
- Example: `UserFactory(groups=['SupportSeeker'])` - useful for testing permission assignment, not model creation

### Known Issues
- **Tox failing on SQLite**: `USE_TZ = False` causes issues with timezone-aware fields in SQLite during testing
  - **Solution needed**: Enable `USE_TZ = True`, store all datetimes as UTC, convert to user timezone in templates/views
  - Current workaround: Use PostgreSQL for tox tests or fix timezone handling

## Code Quality Standards

### What to Remove (Production Cleanup)
1. **Unused Permission Models**: Many `*ObjectPermission` classes exist but are never queried - audit and remove
2. **Dead Code**: Commented code, unused imports, orphaned functions
3. **Over-abstraction**: If a pattern appears once, inline it
4. **Test Factories**: Remove factories that only test Django's built-in model functionality

### Code Patterns to Follow

### Django-Components Pattern
Uses `django-components` v0.141.4 for reusable UI components with `{% element %}` shorthand syntax:

```django
{# templates/account/signup.html #}
{% element panel class="auth_panel__signup" %}
### Permissions with Django Guardian
Object-level permissions assigned via signals for **specific, used permissions only**:

```python
@receiver(post_save, sender=PeerSession)
def set_peersession_permissions(sender, instance, created, **kwargs):
    if instance.is_published:
        assign_perm('view_peersession', support_seeker_group, instance)
    if created:
        assign_perm('change_peersession', instance.host, instance)
```

**Critical**: Only create permission model classes (`*ObjectPermission`) if actually used in queries
- Check permissions: `user.has_perm('events.add_peersession')`
- Query by permission: `get_objects_for_user(user, 'events.view_peersession')`
- **Audit needed**: Many permission models exist but may never be queried
Object-level permissions assigned via signals (`apps/events/signals.py`, `apps/accounts/signals.py`):

```python
@receiver(post_save, sender=PeerSession)
def set_peersession_permissions(sender, instance, created, **kwargs):
    if instance.is_published:
        assign_perm('view_peersession', support_seeker_group, instance)
    if created:
        assign_perm('change_peersession', instance.host, instance)
```

- Custom permission models: `PeerSessionUserObjectPermission`, `PeerSessionGroupObjectPermission`
- User mixin: `UserGroupPermissionsMixin` for group-based checks
- Check permissions: `user.has_perm('events.add_peersession')` or `get_objects_for_user(user, 'events.view_peersession')`
### Settings Structure
Multi-file settings in `neuromancers/settings/`:
- `base.py` - Core Django/Wagtail settings
- `dev.py`, `production.py` - Environment-specific overrides
- `countries.py`, `currencies.py`, `languages.py` - ISO data lists (imported as constants)
- Control via `ENVIRONMENT` env var (`development`, `production`)

**Database**: SQLite for development (`db.sqlite3`), PostgreSQL recommended for production

## Critical Issues to Address

1. **Timezone Handling (`USE_TZ = False`)**:
   - Current: Naive datetimes, tox tests fail on SQLite
   - Required: Set `USE_TZ = True`, store UTC, convert client-side
   - All datetime fields should be timezone-aware for production

2. **Permission Model Bloat**:
   - 20+ `*ObjectPermission` classes exist across models
   - Many never queried - audit with `grep_search` for actual usage
   - Remove unused classes to reduce database tables and complexity

3. **Documentation Gaps**:
   - No comprehensive README explaining architecture
   - No CONTRIBUTING.md with coding standards
   - Missing inline documentation for complex business logic
**Critical**: SQLite database (`db.sqlite3`), no Postgres required for development

## Integration Patterns

### Stripe Connect
- Host users authorize Stripe accounts via OAuth: `StripeAuthorizeView`, `StripeAuthorizeCallbackView`
- Decorator: `@stripe_account_required` prevents session creation without connected account
- Application fee: 15% (`STRIPE_APPLICATION_FEE = 0.15`)

### Whereby API
- API key in `.env`: `WHEREBY_API_KEY`
- Used for video room creation (implementation in events app)

### Static Assets
- Sass source: `assets/scss/styles.scss` → compiled to `assets/css/styles.css`
- SVG sprites: `assets/icons/*.svg` → `templates/includes/sprite.svg` via `scripts/load_icons.sh`
- Heroicons available via `{% load heroicons %}` (third-party package)
- Compression: django-compressor enabled for production

## Common Gotchas

1. **Always run `make django-collectstatic`** after CSS/icon changes - compiles Sass AND generates SVG sprites, not just copying files
2. **URL routing**:
   - Django admin: `/django-admin/` (dev only)
   - Wagtail admin: `/admin/`
   - Auth: `/login/`, `/signup/` (django-allauth)
3. **Migrations**: Models in subdirectories still generate migrations in app's `migrations/` folder
4. **Custom User model**: `AUTH_USER_MODEL = "accounts.User"` - always import with `get_user_model()`
5. **Template caching**: `cached.Loader` enabled - restart server if template changes don't appear
6. **Timezone issue**: `USE_TZ = False` breaks SQLite tests - needs fixing before production handoff

## File Patterns

- Model imports: `apps/*/models.py` imports from `models_*/`
- Management commands: `apps/*/management/commands/*.py`
- Factories: `apps/*/factories.py` (factory-boy)
- Forms: `apps/*/forms.py`, form fields: `apps/events/form_fields.py`
- Signals: `apps/*/signals.py` (auto-connected via AppConfig)
- Wagtail hooks: `apps/*/wagtail_hooks.py`
- Template tags: `apps/*/templatetags/`

## External Dependencies

- **uv** for Python package management (not pip directly)
- **Dart Sass** for CSS compilation
- **Make** for task automation
- Requirements: `requirements/base.in` → compile with `make update-requirements` → generates `base.txt`
