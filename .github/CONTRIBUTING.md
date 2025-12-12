# Contributing to NEUROMANCERS Community Platform

This document outlines coding standards and development practices for the NEUROMANCERS platform. This is production code intended for client handoff - maintain high standards.

## Core Principles

### DRY (Don't Repeat Yourself)
- Extract repeated patterns into reusable functions, mixins, or components
- Use abstract base classes for common model patterns (see `AbstractSession`, `AbstractAvailability`)
- Create django-components for repeated UI elements
- Consolidate business logic in model methods or utility functions

**Example**:
```python
# ❌ Bad: Repeated logic
class PeerSession(models.Model):
    def can_user_edit(self, user):
        return user.has_perm('change_peersession', self)

class GroupSession(models.Model):
    def can_user_edit(self, user):
        return user.has_perm('change_groupsession', self)

# ✅ Good: Abstract base class
class AbstractSession(models.Model):
    class Meta:
        abstract = True

    def can_user_edit(self, user):
        perm = f'change_{self._meta.model_name}'
        return user.has_perm(perm, self)
```

### KISS (Keep It Simple, Stupid)
- Favor explicit code over clever abstractions
- If a pattern only appears once, don't abstract it
- Use Django/Wagtail conventions rather than custom solutions
- Prioritize readability over brevity

**Example**:
```python
# ❌ Bad: Over-engineered
def get_session_class(session_type):
    return globals()[f'{session_type.title()}Session']

# ✅ Good: Explicit dictionary
SESSION_TYPE_MAP = {
    'peer': PeerSession,
    'group': GroupSession,
}
```

### SOLID Principles

**Single Responsibility**: Each class/function has one clear purpose
```python
# ✅ Good: Separate concerns
class PeerSession(AbstractSession):
    """Represents a peer-to-peer support session"""
    pass

class PeerSessionAvailability(models.Model):
    """Manages time slots for peer sessions"""
    pass
```

**Open/Closed**: Extend via inheritance, not modification
```python
# ✅ Good: Abstract base allows extension
class AbstractSession(models.Model):
    class Meta:
        abstract = True

    def calculate_price(self, user):
        """Override in subclasses for custom pricing logic"""
        raise NotImplementedError
```

**Liskov Substitution**: Subclasses should work wherever parent classes are expected

**Interface Segregation**: Don't force classes to implement unused methods

**Dependency Inversion**: Depend on abstractions (interfaces), not concrete implementations

### TDD (Test-Driven Development)

**What to Test**:
- ✅ Custom business logic methods
- ✅ Permission checks and authorization
- ✅ Complex queries and filters
- ✅ Signal handlers
- ✅ Edge cases and error handling
- ✅ Integration between components

**What NOT to Test**:
- ❌ Django's built-in functionality (migrations, model creation)
- ❌ Third-party library features
- ❌ Simple getters/setters
- ❌ Database CRUD operations without business logic

**Example**:
```python
# ❌ Bad: Testing Django's functionality
def test_user_creation():
    user = User.objects.create(username='test')
    assert user.username == 'test'

# ✅ Good: Testing business logic
def test_user_can_create_session_only_with_stripe_account():
    user = UserFactory(groups=['Peer'])
    # Without Stripe account
    assert not user.can_create_session()

    # With Stripe account
    StripeAccount.objects.create(user=user, stripe_user_id='acct_123')
    assert user.can_create_session()
```

## Code Organization

### Model Structure

**Multi-file pattern**: Split large model files into subdirectories

```
apps/events/
├── models.py                    # Aggregates all models via star imports
├── models_sessions/
│   ├── __init__.py
│   ├── abstract.py              # AbstractSession, AbstractAvailability
│   ├── peer.py                  # PeerSession, PeerSessionAvailability, PeerSessionRequest
│   └── group.py                 # GroupSession, GroupSessionRequest
└── models_pages/
    ├── wagtail_pages.py         # SessionsIndexPage (RoutablePage)
    └── wagtail_detail_pages.py  # PeerSessionDetailPage, GroupSessionDetailPage
```

**Naming conventions**:
- Models: `PascalCase` (e.g., `PeerSession`)
- Fields: `snake_case` (e.g., `concessionary_price`)
- Methods: `snake_case` (e.g., `can_user_edit()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `STRIPE_APPLICATION_FEE`)

### File Patterns

```
apps/{app_name}/
├── models.py                    # Model aggregation
├── models_{category}/           # Model subdirectories
├── forms.py                     # ModelForms and custom forms
├── form_fields.py               # Custom form fields (if needed)
├── views.py                     # Class-based views
├── signals.py                   # Signal receivers
├── utils.py                     # Helper functions
├── validators.py                # Custom validators
├── decorators.py                # Custom decorators
├── mixins.py                    # Reusable mixins
├── choices.py                   # Field choices (enums)
├── blocks.py                    # Wagtail StreamField blocks
├── factories.py                 # factory-boy factories for testing/seeding
├── wagtail_hooks.py             # Wagtail admin customizations
├── admin.py                     # Django admin configuration
├── management/commands/         # Management commands
└── templatetags/                # Custom template tags
```

## Django Best Practices

### Models

**Always use `get_user_model()`**:
```python
# ❌ Bad
from apps.accounts.models import User

# ✅ Good
from django.contrib.auth import get_user_model
User = get_user_model()
```

**Use `help_text` and `verbose_name`**:
```python
class PeerSession(AbstractSession):
    concessionary_price = models.IntegerField(
        null=True,
        blank=True,
        help_text="Reduced price for support seekers with financial need",
        verbose_name="Concessionary Price"
    )
```

**Add constraints and validators**:
```python
class User(AbstractBaseUser):
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(username__regex=username_safe_characters_re),
                name="username_safe_characters_check",
                violation_error_message=username_safe_characters_message,
            ),
        ]
```

### Views

**Prefer class-based views**:
```python
# ✅ Good: Reusable, composable
class ProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
```

**Use decorators for common patterns**:
```python
@method_decorator(login_required)
@method_decorator(stripe_account_required)
def create_session(self, request):
    # Session creation logic
    pass
```

### Forms

**Use ModelForms where possible**:
```python
class PeerSessionForm(forms.ModelForm):
    class Meta:
        model = PeerSession
        fields = ['title', 'description', 'price', 'concessionary_price']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
```

### Templates

**Use django-components for reusable UI**:
```django
{# templates/includes/session_card.html #}
{% element card class="session-card" %}
    {% slot header %}{{ session.title }}{% endslot %}
    {% slot body %}{{ session.description }}{% endslot %}
    {% slot footer %}£{{ session.price|currency }}{% endslot %}
{% endelement %}
```

**Always escape user content** (Django does this by default):
```django
{# ✅ Good: Auto-escaped #}
<p>{{ user.bio }}</p>

{# ❌ Dangerous: Only if you trust the source #}
<p>{{ user.bio|safe }}</p>
```

## Permissions

### Object-Level Permissions (django-guardian)

**Assign in signals**:
```python
@receiver(post_save, sender=PeerSession)
def set_peersession_permissions(sender, instance, created, **kwargs):
    if created:
        # Grant host permissions
        assign_perm('change_peersession', instance.host, instance)
        assign_perm('delete_peersession', instance.host, instance)

    if instance.is_published:
        # Grant support seeker view permissions
        support_seeker_group = UserGroup.objects.get(name='Support Seeker')
        assign_perm('view_peersession', support_seeker_group, instance)
```

**Only create ObjectPermission models if querying**:
```python
# ✅ Good: Only if you use get_objects_for_user()
class PeerSessionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(PeerSession, on_delete=models.CASCADE)

# ❌ Bad: If never queried, remove this model
```

**Check permissions**:
```python
# User-level check
if user.has_perm('events.change_peersession', session):
    # Allow edit

# Query objects user can access
sessions = get_objects_for_user(user, 'events.view_peersession')
```

## Static Assets

### CSS (Sass)

**File structure**:
```
assets/scss/
├── styles.scss              # Main entry point
├── _variables.scss          # Colors, fonts, breakpoints
├── _mixins.scss             # Reusable mixins
├── components/
│   ├── _buttons.scss
│   ├── _forms.scss
│   └── _cards.scss
└── pages/
    ├── _auth.scss
    └── _sessions.scss
```

**Always run collectstatic after changes**:
```bash
make django-collectstatic  # Compiles Sass + generates sprite + collectstatic
```

### Icons

**SVG sprites** in `assets/icons/` are compiled to `templates/includes/sprite.svg`:
```bash
scripts/load_icons.sh assets/icons templates/includes/sprite.svg
```

**Use in templates**:
```django
{% load static %}
<svg class="icon">
    <use href="{% static 'includes/sprite.svg' %}#icon-name"></use>
</svg>
```

**Heroicons** available via third-party package:
```django
{% load heroicons %}
{% heroicon_outline "user" %}
```

## Database

### Migrations

**Always review generated migrations**:
```bash
make django-makemigrations
# Review the migration file
make django-migrate
```

**Use data migrations for complex changes**:
```python
def forwards_func(apps, schema_editor):
    UserGroup = apps.get_model('accounts', 'UserGroup')
    UserGroup.objects.get_or_create(name='Peer', label='Peer Support Provider')

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forwards_func),
    ]
```

### Queries

**Use `select_related` and `prefetch_related`**:
```python
# ❌ Bad: N+1 queries
sessions = PeerSession.objects.all()
for session in sessions:
    print(session.host.username)  # Hits DB each time

# ✅ Good: Single query
sessions = PeerSession.objects.select_related('host')
for session in sessions:
    print(session.host.username)
```

## Testing

### Factory-boy

**Use for integration tests and seeding**:
```python
# apps/events/factories.py
class PeerSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PeerSession

    host = factory.LazyFunction(get_host_user)
    title = factory.Faker('sentence', nb_words=4)
    price = factory.LazyFunction(stable_price)
```

**Usage in tests**:
```python
def test_session_request_approval():
    session = PeerSessionFactory(is_published=True)
    user = UserFactory(groups=['SupportSeeker'])
    request = PeerSessionRequest.objects.create(session=session, requester=user)

    # Test approval logic
    assert request.status == 'pending'
    request.approve()
    assert request.status == 'approved'
```

### Test Organization

```
apps/{app_name}/
└── tests/
    ├── __init__.py
    ├── test_models.py           # Model method tests
    ├── test_views.py            # View/integration tests
    ├── test_forms.py            # Form validation tests
    ├── test_permissions.py      # Permission logic tests
    └── test_signals.py          # Signal handler tests
```

## Code Quality

### Remove Unused Code

**Audit and remove**:
- Commented-out code (use git history instead)
- Unused imports
- Permission models never queried
- Dead functions/methods
- Over-abstractions used once

### Linting

**Pre-commit hooks** configured:
```bash
make lint-git-files  # Lint tracked files
```

Tools configured in `pyproject.toml`:
- **black**: Code formatting (line length 88)
- **isort**: Import sorting (Django profile)
- **djlint**: Template formatting

### Documentation

**Docstrings for complex logic**:
```python
def calculate_platform_fee(price, concessionary=False):
    """
    Calculate platform fee for a session.

    Args:
        price (int): Session price in smallest currency unit (pence/cents)
        concessionary (bool): Whether concessionary pricing applies

    Returns:
        int: Platform fee amount

    Note:
        Platform takes 15% fee, but waives it for concessionary bookings
    """
    if concessionary:
        return 0
    return int(price * 0.15)
```

**Inline comments for non-obvious decisions**:
```python
# Stripe requires amounts in smallest currency unit (pence, not pounds)
stripe.PaymentIntent.create(amount=price * 100, currency='gbp')
```

## Git Workflow

**Branch naming**:
- `feature/session-availability` - New features
- `fix/timezone-handling` - Bug fixes
- `refactor/permission-models` - Code improvements
- `docs/contributing-guide` - Documentation

**Commit messages**:
```
feat: Add concessionary pricing approval workflow

- Add `require_concessionary_approval` field to AbstractSession
- Create signal to assign approval permissions
- Add approval view and template
- Update tests for new workflow

Closes #123
```

## Environment Configuration

### Settings Structure

```
neuromancers/settings/
├── base.py          # Core settings (import from here)
├── dev.py           # Development overrides (DEBUG=True, console email)
├── production.py    # Production overrides (security settings)
├── countries.py     # ISO country list
├── currencies.py    # ISO currency list
└── languages.py     # ISO language list
```

**Environment control**:
```bash
# .env
ENVIRONMENT=development  # or 'production'
```

### Secret Management

**Never commit secrets**:
- Use `.env` for local development (in `.gitignore`)
- Use secure secrets manager for production
- Reference in settings via `environ.Env()`

```python
# neuromancers/settings/base.py
env = environ.Env(
    DEBUG=(bool, True),
    ENVIRONMENT=(str, 'development'),
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

STRIPE_API_SECRET_KEY = env('STRIPE_API_SECRET_KEY', default='')
```

## Common Pitfalls

### 1. Timezone Handling (⚠️ CRITICAL ISSUE)

**Current state**: `USE_TZ = False` breaks SQLite tests

**Required fix**:
```python
# neuromancers/settings/base.py
USE_TZ = True  # Store all datetimes as UTC
```

Then convert in templates/views:
```python
# views.py
from django.utils import timezone

now = timezone.now()  # Timezone-aware datetime

# templates
{{ session.start_time|timezone:"Europe/London" }}
```

### 2. Template Caching

**Issue**: Template changes don't appear

**Solution**: Restart dev server or disable caching:
```python
# neuromancers/settings/dev.py
TEMPLATES[0]['OPTIONS']['loaders'] = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django_components.template_loader.Loader',
]
```

### 3. Collectstatic Not Just Copying

**Important**: `make django-collectstatic` does MORE than copy files:
1. Compiles Sass (`assets/scss/styles.scss` → `assets/css/styles.css`)
2. Generates SVG sprite (`scripts/load_icons.sh`)
3. Runs Django's collectstatic

Always run after CSS/icon changes.

### 4. Custom User Model

**Always use**:
```python
from django.contrib.auth import get_user_model
User = get_user_model()
```

**Never use**:
```python
from apps.accounts.models import User  # ❌ Breaks if AUTH_USER_MODEL changes
```

## Production Checklist

Before handoff:

- [ ] Enable `USE_TZ = True` and fix timezone handling
- [ ] Audit and remove unused `*ObjectPermission` models
- [ ] Remove dead code (commented code, unused imports)
- [ ] Add docstrings to all complex business logic
- [ ] Ensure all tests pass (`make django-test`)
- [ ] Run linters (`make lint-git-files`)
- [ ] Configure production settings (SECRET_KEY, ALLOWED_HOSTS, database)
- [ ] Set up static file serving (self-hosted or Django static files)
- [ ] Configure email backend (SMTP)
- [ ] Set up error monitoring (self-hosted solution)
- [ ] Document deployment process

## Questions?

For architectural decisions or complex patterns, refer to:
- `.github/copilot-instructions.md` - AI agent guidance
- `README.md` - Project overview
- Django/Wagtail documentation links in README

When in doubt, prioritize:
1. **Simplicity** over cleverness
2. **Readability** over brevity
3. **Django conventions** over custom solutions
4. **Production readiness** over quick hacks
