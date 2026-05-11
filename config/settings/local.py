import os
from pathlib import Path

# Load env files into os.environ BEFORE importing base so DATABASE_URL etc.
# are available to all Env() instances. This allows the settings to work
# both in Docker and directly on the host.
# ------------------------------------------------------------------------------
_local_env_dir = Path(__file__).resolve(strict=True).parent.parent.parent / ".envs" / ".local"
for _env_file in [_local_env_dir / ".django", _local_env_dir / ".postgres"]:
    if _env_file.exists():
        with open(_env_file) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#"):
                    _key, _sep, _val = _line.partition("=")
                    if _sep and _key.strip():
                        os.environ.setdefault(_key.strip(), _val.strip())

# Construct DATABASE_URL from individual POSTGRES_* vars if not already set.
# The Docker entrypoint does this, but on the host we need to do it ourselves.
# ------------------------------------------------------------------------------
if "DATABASE_URL" not in os.environ:
    _pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    _pg_port = os.environ.get("POSTGRES_PORT", "5432")
    _pg_db = os.environ.get("POSTGRES_DB", "neuromancers_network")
    _pg_user = os.environ.get("POSTGRES_USER", "neuromancers")
    _pg_pass = os.environ.get("POSTGRES_PASSWORD", "")
    os.environ["DATABASE_URL"] = f"postgres://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"

from .base import *  # noqa: F403
from .base import INSTALLED_APPS
from .base import MIDDLEWARE
from .base import env

DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="Ogn9xlj6fZD5cqHD1n5JrZUBEiJhImJa1Wr4TlV4FreCO8ngEgLyP6essO1QrBSU",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "host.docker.internal"]  # noqa: S104

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}

# STORAGES
# ------------------------------------------------------------------------------
# Use in-memory storage for media files to skip AWS S3 dependency in local dev.
# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-STORAGES
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
# Use console backend in local dev so emails are printed to stdout (no SMTP needed).
# Override with DJANGO_EMAIL_BACKEND env var if you want to use Mailpit or another backend.
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = env("EMAIL_HOST", default="mailpit")
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]


# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ["debug_toolbar"]
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": [
        "debug_toolbar.panels.redirects.RedirectsPanel",
        # Disable profiling panel due to an issue with Python 3.12+:
        # https://github.com/jazzband/django-debug-toolbar/issues/1875
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ],
    "SHOW_TEMPLATE_CONTEXT": True,
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
if env.bool("USE_DOCKER", default=False):
    import socket

    try:
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        INTERNAL_IPS += [".".join([*ip.split(".")[:-1], "1"]) for ip in ips]
    except (socket.gaierror, OSError):
        pass

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]

# Celery (eager mode — all tasks run synchronously, no Redis worker required)
# ------------------------------------------------------------------------------
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-always-eager
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True

# Your stuff...
# ------------------------------------------------------------------------------
