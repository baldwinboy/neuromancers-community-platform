# NEUROMANCERS Community Platform

Production-ready Django/Wagtail CMS for scheduling peer support sessions with integrated payment processing and video conferencing.

![Coverage](reports/coverage-badge.svg?branch=main)

## Overview

This platform enables peer support providers to:
- Create and manage peer-to-peer and group support sessions
- Set availability windows and pricing (including concessionary rates)
- Receive session requests from support seekers
- Process payments through Stripe Connect (15% platform fee)
- Conduct sessions via Whereby video conferencing integration

Support seekers can:
- Browse published sessions with filtering (language, duration, topic, etc.)
- Request sessions and await approval
- Access concessionary pricing (with approval)
- Join video sessions after payment

## Tech Stack

- **Backend**: Django 6.0, Wagtail 7.3
- **Authentication**: django-allauth 65.x (email/username, magic links)
- **Permissions**: django-guardian 3.x (object-level permissions)
- **Payments**: Stripe Connect (OAuth, payment links)
- **Video**: Whereby API
- **Frontend**: Sass, django-components 0.148.0, Heroicons
- **Database**: SQLite (development), PostgreSQL (production recommended)
- **Package Manager**: uv (faster than pip)
- **Task Runner**: GNU Make

## Requirements

- [GNU Make](https://www.gnu.org/software/make/)
- [uv](https://docs.astral.sh/uv/) (Python package installer)
- [Dart Sass](https://sass-lang.com/install/) (CSS compilation)
- Python 3.12

## Quick Start

### Initial Setup

```bash
# 1. Create virtual environment
make venv
source .venv/neuromancers/bin/activate

# 2. Configure environment variables
cp .env.development .env
# Edit .env with your Stripe/Whereby credentials if needed

# 3. Fresh install (migrations, superuser, static files, run server)
make fresh
```

The development server will start at **http://localhost:8000**

**Default superuser credentials**: `_neuro` / `_default_password`

### Subsequent Runs

```bash
source .venv/neuromancers/bin/activate
make dev  # Runs migrations, collectstatic, starts server
```

## Project Structure

```
neuromancers-community-platform/
├── apps/
│   ├── accounts/       # User model, authentication, profiles, Stripe accounts
│   │   ├── models_users/
│   │   │   ├── user.py           # Custom User, UserGroup
│   │   │   ├── profile.py        # Profile, Certificate, StripeAccount
│   │   │   └── user_settings.py  # Notification/filter/privacy preferences
│   ├── events/         # Session management
│   │   ├── models_sessions/
│   │   │   ├── abstract.py       # AbstractSession, AbstractAvailability, AbstractSessionRequest, AbstractSessionReview
│   │   │   ├── peer.py           # PeerSession, PeerSessionAvailability, PeerSessionRequest, PeerScheduledSession, PeerSessionReview
│   │   │   └── group.py          # GroupSession, GroupSessionRequest, GroupSessionReview
│   │   ├── models_pages/
│   │   │   ├── wagtail_pages.py  # SessionsIndexPage (RoutablePage)
│   │   │   ├── wagtail_detail_pages.py  # PeerSessionDetailPage, GroupSessionDetailPage
│   │   │   └── wagtail_settings.py      # StripeSettings, WherebySettings, SessionFilterSettings, SocialMediaSettings
│   │   ├── components/  # session_item, peer_item, request_calendar, session_feed, peer_feed
│   │   └── forms_sessions/  # Peer and group session forms
│   ├── core/           # HomePage, reusable components (accordion, hero), notification/site settings
│   ├── common/         # Shared utilities (GetPronto image uploads, helpers)
│   ├── blog/           # Blog index and blog pages
│   └── contact/        # Contact form with topics
├── neuromancers/settings/
│   ├── base.py         # Core settings (USE_TZ=True, TIME_ZONE="UTC")
│   ├── dev.py          # Development overrides (DEBUG=True, console email)
│   ├── production.py   # Production overrides (security headers, HSTS)
│   ├── countries.py, currencies.py, languages.py  # ISO data lists
│   ├── stripe_currencies.py  # Stripe-supported currencies
│   ├── blacklist.py    # Username blacklist
│   └── bots.py         # Bot user agent list (production)
├── templates/          # Django templates
├── assets/             # Source Sass, icons, images
└── static/             # Compiled static files (generated)
```

## Key Concepts

### Multi-File Model Architecture

Models are organized in subdirectories and aggregated via star imports:

```python
# apps/events/models.py
from .models_pages.wagtail_pages import *
from .models_pages.wagtail_settings import *
from .models_sessions.peer import *
from .models_sessions.group import *
```

This keeps large model files manageable. All migrations still generate in `apps/events/migrations/`.

### Wagtail RoutablePage Pattern

`SessionsIndexPage` serves dual purpose:
1. **CMS page** - editable content in Wagtail admin
2. **Application routes** - custom URL patterns for session CRUD:
   - `/sessions/create/` - Choose session type
   - `/sessions/create/<session_type>/` - Create peer or group session
   - `/sessions/edit/<session_type>/<uuid>/` - Edit session
   - `/sessions/availability/<uuid>/` - Manage peer session availability
   - `/sessions/availability/delete/<uuid>/` - Delete availability slot
   - `/sessions/request/schedule/<uuid>/` - Request/schedule a peer session

Each session creates a child Wagtail page (`PeerSessionDetailPage`) for SEO and CMS integration.

### Object-Level Permissions

Uses django-guardian with signal-based assignment:

```python
# apps/events/signals.py
@receiver(post_save, sender=PeerSession)
def set_peersession_permissions(sender, instance, created, **kwargs):
    if instance.is_published:
        assign_perm('view_peersession', support_seeker_group, instance)
    if created:
        assign_perm('change_peersession', instance.host, instance)
```

- **Support Seekers** can view published sessions, request sessions
- **Peers** can create/edit their own sessions, manage availability
- **Neuromancers** have admin-level permissions

### Component Systems

The project uses two separate component systems:

**1. django-components** (v0.148.0) — reusable UI with shorthand template tags:

```django
{% accordion %}...{% endaccordion %}
{% hero heading="Welcome" subheading="Join our community" %}
{% session_item session=session_data session_type="peer" %}
{% peer_item peer=peer_data %}
{% request_calendar available_slots=slots durations=durations %}
```

Components registered in `apps/core/components/` (`accordion`, `hero`) and `apps/events/components/` (`session_item`, `peer_item`, `request_calendar`).

**2. Wagtail Component** (`laces` package) — for complex feed blocks:
- `SessionFeedBlock` and `PeerFeedBlock` in `apps/events/components/` extend `wagtail.blocks.StructBlock`
- Rendered via Wagtail's StreamField block system

**Note**: `{% element %}` tags in `templates/allauth/elements/` are django-allauth's own element system, not django-components.

## Development Commands

### Common Tasks

```bash
# Database
make django-migrate              # Apply migrations
make django-makemigrations       # Create new migrations

# Static Assets (ALWAYS RUN AFTER CSS/ICON CHANGES)
make django-collectstatic        # Compiles Sass + generates sprite + collectstatic
make sass-watch                  # Watch Sass for changes

# Development
make django-runserver            # Start development server
make django-shell                # Django shell
make django-test                 # Run test suite

# Data Seeding
make django-setupdefaultgroups   # Create UserGroups (Peer, Support Seeker, Neuromancer)
make django-publishsessionsindex # Publish unpublished SessionsIndexPages
make django-seedusers USERS=50 GROUPS="Peer"  # Generate test users
make django-seedsessions SIZE=50 # Generate test sessions

# Code Quality
make lint-git-files              # Run pre-commit on tracked files
make django-coverage             # Run tests with coverage + HTML report
make django-coverage-badge       # Generate coverage badge SVG
```

### Environment Variables

Key variables in `.env`:

```bash
DEBUG=true
DJANGO_SECRET_KEY=your-secret-key
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Stripe Connect
STRIPE_API_PUBLISHABLE_KEY=pk_test_...
STRIPE_API_SECRET_KEY=sk_test_...
STRIPE_API_CLIENT_ID=ca_...
STRIPE_REDIRECT_URL=

# Whereby Video API
WHEREBY_API_KEY=your-whereby-key

# GetPronto (profile image uploads)
GETPRONTO_API_KEY=
GETPRONTO_API_URL=https://api.getpronto.io/v1

# Email (console backend in dev)
EMAIL_HOST=localhost
EMAIL_PORT=25
```

## Testing

```bash
make django-test           # Run full test suite
make django-coverage       # Run tests with coverage report and HTML output
tox -e coverage            # Run coverage via tox (with uv support)
```

Coverage reports are generated in `reports/coverage/` directory after running coverage commands.

**Testing Philosophy**:
- Test business logic, not Django framework functionality
- Models are validated by successful migrations
- Focus on custom methods, permissions, edge cases
- Use factories (`UserFactory`, `PeerSessionFactory`) for integration tests only

## Known Issues & Roadmap

### Pre-Handoff Tasks

1. **Code Cleanup**:
   - Audit 24 `*ObjectPermission` classes (16 in accounts, 8 in events) — many never queried directly
   - Remove unused permission models
   - Clean up commented code, unused imports

2. **Documentation**:
   - Complete inline documentation for business logic
   - Add docstrings to complex methods
   - Document session request > approval > payment flow

## Admin Access

- **Wagtail CMS Admin**: http://localhost:8000/admin/
- **Django Admin** (dev only): http://localhost:8000/django-admin/
- **Auth Pages**: `/login/`, `/signup/`, `/password/reset/`

## Integration Details

### Stripe Connect

Peers must connect their Stripe account before creating sessions:

1. Navigate to `/stripe/authorize/`
2. Complete OAuth flow on Stripe
3. Callback to `/stripe/oauth/callback/` stores credentials
4. `@stripe_account_required` decorator enforces this on session creation

Platform takes 15% application fee (`STRIPE_APPLICATION_FEE = 0.15`).

### Whereby Rooms

Video rooms created via Whereby API when sessions are scheduled. API key configured in `WHEREBY_API_KEY`.

## Deployment

**Note**: Deployment configuration pending. Current setup:
- SQLite for development
- Recommend PostgreSQL for production
- Static files served via Django's static file handling or self-hosted solution
- Media files stored on self-hosted infrastructure
- Environment variables via secure secrets management (password manager, encrypted vaults)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for coding standards and development workflow.

## Documentation Links

- [Django 6.0](https://docs.djangoproject.com/en/6.0/)
- [Wagtail 7](https://docs.wagtail.org/en/stable/)
- [django-allauth](https://docs.allauth.org/en/latest/)
- [django-guardian](https://django-guardian.readthedocs.io/)
- [Stripe Connect](https://docs.stripe.com/connect)
- [Whereby API](https://docs.whereby.com/)
- [django-components](https://github.com/EmilStenstrom/django-components)

## License

[License information to be added]
