"""Local development settings with zero external dependencies.

Runs entirely with SQLite, in-memory cache, and console email —
no Docker, PostgreSQL, Redis, or Mailpit required.

Usage::

    python manage.py migrate --settings=config.settings.dev
    python manage.py runserver --settings=config.settings.dev

Stripe features (checkout, webhooks, Connect) need API keys.
Set them through the Wagtail CMS at /cms/settings/ after login,
or create ``.envs/.local/.django`` with ``STRIPE_TEST_SECRET_KEY``
and run with ``DJANGO_READ_DOT_ENV_FILE=True``.
"""

import os
from pathlib import Path

# Set DATABASE_URL before importing base so the env.db() call succeeds.
# SQLite — no PostgreSQL server needed for local development.
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'dev.db'}",
)

from .base import *  # noqa: F403
from .base import INSTALLED_APPS
from .base import MIDDLEWARE
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="dev-secret-key-do-not-use-in-production",
)
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}

# STORAGES
# ------------------------------------------------------------------------------
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# EMAIL
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# WhiteNoise
# ------------------------------------------------------------------------------
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]

# django-debug-toolbar
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": [
        "debug_toolbar.panels.redirects.RedirectsPanel",
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ],
    "SHOW_TEMPLATE_CONTEXT": True,
}
INTERNAL_IPS = ["127.0.0.1"]

# Rate limiting (use in-memory backend — no Redis required)
# ------------------------------------------------------------------------------
# The default ``MemoryBackend`` path in django_smart_ratelimit is incorrect;
# point it at the actual module.
RATELIMIT_BACKEND = "django_smart_ratelimit.backends.memory.MemoryBackend"

# django-extensions
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["django_extensions"]

# Celery (eager mode — all tasks run synchronously, no Redis worker required)
# ------------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# dj-stripe
# ------------------------------------------------------------------------------
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"  # for development
DEFAULT_FROM_EMAIL = "no-reply@yourdomain.com"
