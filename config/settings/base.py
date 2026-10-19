# ruff: noqa: E501
"""Base settings to build other settings files upon."""

import ssl
from pathlib import Path

import environ
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# neuromancers_network/
APPS_DIR = BASE_DIR / "neuromancers_network"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-GB"
# https://docs.djangoproject.com/en/dev/ref/settings/#languages
# Code-level supported superset. The admin curates the offered subset at runtime
# via LocalizationSettings; Wagtail reads this list at startup, so any language
# the admin may enable must be present here.
LANGUAGES = [
    ("en", _("English")),
    ("fr", _("French")),
    ("de", _("German")),
    ("es", _("Spanish")),
    ("pt", _("Portuguese")),
]
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # Handy template tags
    "django.contrib.admin",
    "django.contrib.postgres",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "colorfield",
    "django_celery_beat",
    "corsheaders",
    "auditlog",
    "django_fsm",
    "djstripe",
    "rules",
    "wagtailcharts",
]

ALLAUTH_APPS = [
    "allauth",
    "allauth.account",
]

WAGTAIL_APPS = [
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.settings",
    "wagtail.contrib.simple_translation",
    "wagtail.contrib.table_block",
    "wagtail.embeds",
    "wagtail.sites",
    "config.apps.CustomUsersAppConfig",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_htmx",
    "draftail_text_utils",
]

# wagtail_daisIE must initialise before allauth and the project apps.
DAISIE_APPS = [
    "wagtail_daisIE",
    "wagtail_daisIE.assets",
    "wagtail_daisIE.menus",
    "wagtail_daisIE.feeds",
    "wagtail_daisIE.errors",
    "wagtail_daisIE.notifications",
    "wagtail_daisIE.allauth_ui",
    "wagtail_daisIE.allauth_emails",
]

LOCAL_APPS = [
    "neuromancers_network.core",
    "neuromancers_network.users",
    # Your stuff: custom apps go here
    "neuromancers_network.peers",
    "neuromancers_network.meetings",
    "neuromancers_network.payments",
    "neuromancers_network.taxonomy",
    "neuromancers_network.inbox",
    "neuromancers_network.moderation",
    "neuromancers_network.analytics",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = [
    *DJANGO_APPS,
    *THIRD_PARTY_APPS,
    *WAGTAIL_APPS,
    *DAISIE_APPS,
    *ALLAUTH_APPS,
    *LOCAL_APPS,
]

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "neuromancers_network.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "rules.permissions.ObjectPermissionBackend",
    "neuromancers_network.users.backends.SigninGuardModelBackend",
    "neuromancers_network.users.backends.SigninGuardAllauthBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "/dashboard/"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "neuromancers_network.core.middleware.LocalizationMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]
# htmx support for daisIE feeds, actions and form blocks.
MIDDLEWARE.append("django_htmx.middleware.HtmxMiddleware")
# Admin-authored arbitrary CSS.
MIDDLEWARE.append("wagtail_daisIE.middleware.ArbitraryCSSMiddleware")
# IP-ban enforcement (shadow mode until enabled in Ban Settings).
MIDDLEWARE.append("neuromancers_network.moderation.middleware.BanMiddleware")

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# STORAGES
# ------------------------------------------------------------------------------
# Private data exports use a dedicated storage so they never land in the public
# media bucket. Development and tests use the local filesystem; production maps
# the ``exports`` alias onto the private backups bucket (see production.py).
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "exports": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": str(APPS_DIR / "exports"),
            "base_url": "/exports/",
        },
    },
}

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
                "neuromancers_network.users.context_processors.allauth_settings",
                "neuromancers_network.core.context_processors.localization",
                "neuromancers_network.core.context_processors.daisie_themes",
                "neuromancers_network.core.context_processors.site_scripts",
            ],
        },
    },
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="neuromancers_network.core.mailer.WagtailEmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="NEUROMANCERS Network <noreply@neuromancers.org.uk>",
)

# ADMIN
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = ["hello@neuromancers.org.uk"]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")
REDIS_SSL = REDIS_URL.startswith("rediss://")

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = REDIS_URL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#redis-backend-use-ssl
CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE} if REDIS_SSL else None
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = REDIS_URL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#redis-backend-use-ssl
CELERY_REDIS_BACKEND_USE_SSL = CELERY_BROKER_USE_SSL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
CELERY_RESULT_EXTENDED = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-always-retry
# https://github.com/celery/celery/pull/6122
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-max-retries
CELERY_RESULT_BACKEND_MAX_RETRIES = 10
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_TIME_LIMIT = 5 * 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-soft-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_SOFT_TIME_LIMIT = 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-send-task-events
CELERY_WORKER_SEND_TASK_EVENTS = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-task_send_sent_event
CELERY_TASK_SEND_SENT_EVENT = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-hijack-root-logger
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
# django-allauth
# ------------------------------------------------------------------------------
# Decoy field for spam detection
# Requires a field not used on sign up
ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = "is_staff"
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_SUPPORTS_RESEND = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_EMAIL_NOTIFICATIONS = True
ACCOUNT_PRESERVE_USERNAME_CASING = False
# Username badlist is admin-managed (ModerationSettings); keep this empty.
ACCOUNT_USERNAME_BLACKLIST: list[str] = []
ACCOUNT_CHANGE_EMAIL = True

# Users can request email confirmation mails via the email management view, and, implicitly, when logging in with an unverified account. This rate limit prevents users from sending too many of these mails.
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_SIGNUP_FIELDS = [
    "username*",
    "email*",
    "email2*",
    "password1*",
    "password2*",
]
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_ADAPTER = "neuromancers_network.users.adapters.AccountAdapter"
# https://docs.allauth.org/en/latest/account/forms.html
ACCOUNT_FORMS = {
    "signup": "neuromancers_network.users.forms.UserSignupForm",
    "add_email": "neuromancers_network.users.forms.AddEmailForm",
}

# dj-stripe
# ------------------------------------------------------------------------------
# https://dj-stripe.dev/dj-stripe/2.11/reference/settings/#djstripe_foreign_key_to_field
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# Wagtail
# -----------------------------------------------------------------------------
# https://docs.wagtail.org/en/stable/getting_started/integrating_into_django.html
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000
WAGTAIL_SITE_NAME = "NEUROMANCERS Network"
WAGTAILADMIN_BASE_URL = env(
    "WAGTAILADMIN_BASE_URL",
    default="https://network.neuromancers.org.uk",
)
WAGTAILDOCS_EXTENSIONS = [
    "csv",
    "docx",
    "key",
    "odt",
    "pdf",
    "pptx",
    "rtf",
    "txt",
    "xlsx",
    "zip",
]
WAGTAILADMIN_LOGIN_URL = reverse_lazy("account_login")
# Content i18n is toggled at runtime from LocalizationSettings.enabled (0.11);
# Wagtail reads this flag at startup, so it is set here and the middleware syncs
# the active locale per request.
WAGTAIL_I18N_ENABLED = True
WAGTAILSEARCH_BACKENDS = {
    "default": {"BACKEND": "wagtail.search.backends.database"},
}
# Wagtail will not be able to create pages with the following routes
WAGTAIL_RESERVED_ROUTES = [
    "2fa",
    "3rdparty",
    ".well-known",
    "admin",
    "accounts",
    "api",
    "clients",
    "cms",
    "confirm-email",
    "daisie",
    "device",
    "documents",
    "email",
    "health",
    "identity",
    "idp",
    "inactive",
    "login",
    "logout",
    "media",
    "oauth",
    "oidc",
    "password",
    "phone",
    "reauthenticate",
    "revoke",
    "static",
    "stripe",
    "signup",
    "social",
    "sessions",
    "token",
    "userinfo",
]

# Wagtail daisIE
# ------------------------------------------------------------------------------
# https://pypi.org/project/wagtail-daisie/
# htmx integration (django-htmx) for feeds, actions and form blocks.
WAGTAIL_DAISIE_HTMX = True
WAGTAIL_DAISIE_HTMX_VERSION = 2
# Render allauth pages (login/signup/etc.) with the DaisyUI theme overrides.
WAGTAIL_DAISIE_ALLAUTH_UI = True
# Chrome used to render allauth pages (read by wagtail_daisIE >= 2.0.0).
WAGTAIL_DAISIE_ALLAUTH_BASE_TEMPLATE = "base.html"
WAGTAIL_DAISIE_HEADER_MENU = "Main navigation"
WAGTAIL_DAISIE_FOOTER_MENU = "Footer"
# Content page types allowed in the generic page-tree feeds. Forms, indexes,
# detail pages and system pages are implicitly excluded by this allowlist.
WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = [
    "core.StandardPage",
]
# Shared by the generic page-tree feed context models. Filter labels are plain
# str (not gettext_lazy) so they stay JSON-safe for the admin.
_PAGE_FEED_FILTERS = {
    "search": {
        "type": "search",
        "field": "title",
        "fields": ["title", "search_description"],
        "label": "Search",
    },
    "published": {
        "type": "date_range",
        "field": "first_published_at",
        "label": "Published",
    },
}
# Feed filters for meetings and care-provider profiles. ISO codes/slugs are
# offered as choices; the `query` callables resolve them and preserve the
# faceted search semantics. Per-tag-group filters are appended at runtime
# (neuromancers_network.taxonomy.selectors.install_tag_group_filters).
_MEETING_FILTERS = {
    "search": {
        "type": "search",
        "field": "title",
        "fields": ["title", "description"],
        "label": "Search",
    },
    "language": {
        "type": "choice",
        "field": "languages",
        "multi": True,
        "autocomplete": True,
        "label": "Language",
        "choices": "neuromancers_network.taxonomy.selectors.language_choices",
        "query": "neuromancers_network.taxonomy.selectors.meeting_language_query",
    },
    "country": {
        "type": "choice",
        "field": "countries",
        "multi": True,
        "autocomplete": True,
        "label": "Country",
        "choices": "neuromancers_network.taxonomy.selectors.country_choices",
        "query": "neuromancers_network.taxonomy.selectors.meeting_country_query",
    },
    "tag": {
        "type": "choice",
        "field": "tags",
        "multi": True,
        "autocomplete": True,
        "label": "Tag",
        "choices": "neuromancers_network.taxonomy.selectors.tag_choices",
        "query": "neuromancers_network.taxonomy.selectors.meeting_tag_query",
    },
    "meeting_type": {
        "type": "choice",
        "field": "meeting_type",
        "label": "Meeting type",
        "choices": [("1:1", "1:1"), ("group", "Group")],
    },
    "pricing_type": {
        "type": "choice",
        "field": "pricing_type",
        "multi": True,
        "label": "Pricing type",
        "choices": [
            ("per_hour", "Per hour"),
            ("fixed", "Fixed price"),
            ("sliding_scale", "Sliding scale"),
            ("duration_tiers", "Duration tiers"),
        ],
    },
    "schedule": {
        "type": "date_range",
        "field": "scheduled_at",
        "label": "Schedule",
    },
    "amount": {
        "type": "number_range",
        "field": "price",
        "label": "Price",
        "query": "neuromancers_network.taxonomy.selectors.meeting_amount_query",
    },
}
_PEER_FILTERS = {
    "search": {
        "type": "search",
        "field": "bio",
        "fields": ["bio"],
        "label": "Search",
    },
    "language": {
        "type": "choice",
        "field": "languages",
        "multi": True,
        "autocomplete": True,
        "label": "Language",
        "choices": "neuromancers_network.taxonomy.selectors.language_choices",
        "query": "neuromancers_network.taxonomy.selectors.peer_language_query",
    },
    "country": {
        "type": "choice",
        "field": "countries",
        "multi": True,
        "autocomplete": True,
        "label": "Country",
        "choices": "neuromancers_network.taxonomy.selectors.country_choices",
        "query": "neuromancers_network.taxonomy.selectors.peer_country_query",
    },
    "tag": {
        "type": "choice",
        "field": "tags",
        "multi": True,
        "autocomplete": True,
        "label": "Tag",
        "choices": "neuromancers_network.taxonomy.selectors.tag_choices",
        "query": "neuromancers_network.taxonomy.selectors.peer_tag_query",
    },
}
# Context models authors may bind into content (block fields, feeds, pages).
WAGTAIL_DAISIE_CONTEXT_MODELS = {
    "user": {
        "label": _("User"),
        "model": "users.User",
        "source": "request.user",
    },
    "meeting": {
        "label": _("Meeting"),
        "model": "meetings.Meeting",
        "source": "url",
        "lookup_field": "meeting_pk",
        "queryset": "neuromancers_network.meetings.selectors.published_meetings",
        "select_related": ["peer"],
        "prefetch_related": ["languages", "countries", "tags"],
        "filters": _MEETING_FILTERS,
    },
    "peer_profile": {
        "label": _("Care provider"),
        "model": "peers.PeerProfile",
        "source": "url",
        "lookup_field": "peer_pk",
        "queryset": "neuromancers_network.peers.selectors.approved_peers",
        "select_related": ["user"],
        "prefetch_related": ["languages", "countries", "tags"],
        "filters": _PEER_FILTERS,
    },
    "my_meeting": {
        "label": _("My meetings"),
        "model": "meetings.Meeting",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.my_meetings",
        "select_related": ["peer"],
        "prefetch_related": ["languages", "countries", "tags"],
    },
    "my_availability": {
        "label": _("My availability"),
        "model": "peers.PeerAvailability",
        "source": "request.user",
        "queryset": "neuromancers_network.peers.selectors.my_availability",
    },
    "blocked_user": {
        "label": _("Blocked member"),
        "model": "users.User",
        "source": "request.user",
        "queryset": "neuromancers_network.moderation.selectors.blocked_users",
    },
    "calendar_event": {
        "label": _("Calendar event"),
        "model": "peers.CalendarEvent",
        "source": "request.user",
        "queryset": "neuromancers_network.peers.selectors.peer_calendar_events",
    },
    "review": {
        "label": _("Review"),
        "model": "meetings.Review",
        "source": "url",
        "lookup_field": "review_pk",
        "queryset": "neuromancers_network.meetings.selectors.published_reviews",
    },
    "my_reviews": {
        "label": _("My reviews"),
        "model": "meetings.Review",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.my_reviews",
        "select_related": ["reviewer", "meeting_request__meeting"],
    },
    "my_pending_reviews": {
        "label": _("My pending reviews"),
        "model": "meetings.Review",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.my_pending_reviews",
        "select_related": ["reviewer", "meeting_request__meeting"],
    },
    "my_published_reviews": {
        "label": _("My published reviews"),
        "model": "meetings.Review",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.my_published_reviews",
        "select_related": ["reviewer", "meeting_request__meeting"],
    },
    "my_hidden_reviews": {
        "label": _("My hidden reviews"),
        "model": "meetings.Review",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.my_hidden_reviews",
        "select_related": ["reviewer", "meeting_request__meeting"],
    },
    "user_profile": {
        "label": _("Member profile"),
        "model": "users.UserProfile",
        "source": "url",
        "lookup_field": "user__username",
        "select_related": ["user"],
    },
    "booking": {
        "label": _("Booking"),
        "model": "meetings.Booking",
        "source": "url",
        "lookup_field": "pk",
        "queryset": "neuromancers_network.meetings.selectors.bookings_for_context",
        "select_related": ["meeting", "meeting__peer", "support_seeker"],
    },
    "payment_history": {
        "label": _("Payment history"),
        "model": "meetings.MeetingRequest",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.user_payment_history",
        "select_related": ["meeting"],
    },
    "unpaid_booking": {
        "label": _("Unpaid booking"),
        "model": "meetings.Booking",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.unpaid_bookings",
        "select_related": ["meeting"],
    },
    "host_meeting": {
        "label": _("Host meeting"),
        "model": "meetings.Meeting",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.my_meetings",
    },
    "host_request": {
        "label": _("Host booking request"),
        "model": "meetings.MeetingRequest",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.host_requests",
        "select_related": ["meeting", "support_seeker"],
    },
    "host_refund": {
        "label": _("Host refund request"),
        "model": "meetings.RefundRequest",
        "source": "request.user",
        "queryset": "neuromancers_network.meetings.selectors.host_refunds",
    },
    "peer_application": {
        "label": _("Peer application"),
        "model": "peers.PeerApplication",
        "source": "neuromancers_network.peers.selectors.user_peer_application",
    },
    "refund_request": {
        "label": _("Refund request"),
        "model": "meetings.RefundRequest",
        "source": "url",
        "lookup_field": "pk",
        "queryset": "neuromancers_network.meetings.selectors.refunds_for_context",
        "select_related": [
            "meeting_request__meeting",
            "meeting_request__support_seeker",
        ],
    },
    "notification_preference": {
        "label": _("Notification preferences"),
        "model": "inbox.NotificationPreference",
        "source": "neuromancers_network.inbox.selectors.user_notification_preference",
    },
    "notification": {
        "label": _("Notification"),
        "model": "inbox.Notification",
        "source": "request.user",
        "queryset": "neuromancers_network.inbox.selectors.user_notifications",
        "filters": {
            "unread": {
                "type": "boolean",
                "field": "read_at",
                "label": "Unread",
                "query": "neuromancers_network.inbox.selectors.notification_unread_query",
            },
        },
    },
    "tag": {
        "label": _("Tag"),
        "model": "taxonomy.AllowedTag",
        "source": "url",
        "lookup_field": "slug",
        "lookup_in": "path",
    },
    "host_page": {
        "label": _("Current page"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.host_page_only",
    },
    "page_sitewide": {
        "label": _("Every page"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.sitewide_pages",
        "filters": _PAGE_FEED_FILTERS,
    },
    "page_all": {
        "label": _("All descendants"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.all_descendants",
        "filters": _PAGE_FEED_FILTERS,
    },
    "page_children": {
        "label": _("Child pages"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.immediate_children",
        "filters": _PAGE_FEED_FILTERS,
    },
    "page_deeper": {
        "label": _("Deeper pages"),
        "model": "wagtailcore.Page",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.deeper_descendants",
        "filters": _PAGE_FEED_FILTERS,
    },
    "tag_page_children": {
        "label": _("Tag pages"),
        "model": "core.TagDetailPage",
        "source": "page",
        "queryset": "neuromancers_network.core.selectors.tag_page_children",
        "filters": _PAGE_FEED_FILTERS,
    },
}
# Business notifications are delivered through the internal inbox event bus and
# rendered by admin-authored daisIE EmailTemplates.
WAGTAIL_DAISIE_NOTIFICATION_FROM_EMAIL = DEFAULT_FROM_EMAIL
# One bridge per inbox event type. `template` matches an EmailTemplate by name
# or template_key (admin-authored); the shared builders resolve the payload and
# the opted-in recipients.
_NOTIFICATION_EVENT_KEYS = [
    "account_created",
    "account_deleted",
    "account_degraded",
    "account_deactivated",
    "account_reactivated",
    "account_deletion_scheduled",
    "account_deletion_cancelled",
    "email_changed",
    "username_changed",
    "user_blocked",
    "user_unblocked",
    "ip_banned",
    "ip_unbanned",
    "email_banned",
    "email_unbanned",
    "report_created",
    "report_resolved",
    "report_rejected",
    "data_export_requested",
    "data_export_ready",
    "peer_published_meeting",
    "peer_approved",
    "peer_application_approved",
    "peer_application_rejected",
    "booking_requested",
    "booking_approved",
    "booking_rejected",
    "booking_paid",
    "booking_completed",
    "booking_cancelled",
    "refund_requested",
    "refund_approved",
    "refund_rejected",
    "refund_refunded",
    "review_created",
    "review_pending_approval",
    "review_published",
    "review_hidden",
    "subscription_created",
    "subscription_cancelled",
    "subscription_paused",
    "subscription_resumed",
    "payment_succeeded",
    "payment_failed",
    "payment_reminder_due",
    "meeting_upcoming",
    "meeting_cancelled",
    "meeting_unpublished",
    "meetings_unpublished",
    "meetings_deleted",
    "session_reminder_1d",
    "session_reminder_1h",
]
WAGTAIL_DAISIE_NOTIFICATION_BRIDGES = {
    key: {
        "label": key.replace("_", " ").title(),
        "template": key,
        "context": "neuromancers_network.inbox.bridges.context_from_payload",
        "recipients": "neuromancers_network.inbox.bridges.recipients_from_payload",
    }
    for key in _NOTIFICATION_EVENT_KEYS
}
# Labels must be JSON-serialisable: daisIE injects this dict into the admin via
# json.dumps() (wagtail_daisIE/wagtail_hooks.py). Do not use gettext_lazy here.
WAGTAIL_DAISIE_AUDIENCE_RULES = {
    "authenticated": {
        "label": "Signed-in members",
        "rule": "neuromancers_network.core.audience.is_authenticated",
        "queryset": "neuromancers_network.core.audience.authenticated_users",
    },
    "peer": {
        "label": "Care providers",
        "rule": "neuromancers_network.core.audience.is_peer",
        "queryset": "neuromancers_network.core.audience.peer_users",
    },
    "verified_peer": {
        "label": "Verified care providers",
        "rule": "neuromancers_network.core.audience.is_verified_peer",
        "queryset": "neuromancers_network.core.audience.verified_peer_users",
    },
    "peer_owner": {
        "label": "Care providers viewing their own profile",
        "rule": "neuromancers_network.core.audience.is_peer_owner",
    },
    "moderator": {
        "label": "Moderators",
        "rule": "neuromancers_network.core.audience.is_moderator",
        "queryset": "neuromancers_network.core.audience.moderator_users",
    },
    "needs_tos_acceptance": {
        "label": "Members yet to accept the Terms",
        "rule": "neuromancers_network.core.audience.needs_tos_acceptance",
        "queryset": ("neuromancers_network.core.audience.needs_tos_acceptance_users"),
    },
    "deactivated": {
        "label": "Deactivated members",
        "rule": "neuromancers_network.core.audience.is_deactivated",
        "queryset": "neuromancers_network.core.audience.deactivated_users",
    },
    "meeting_host": {
        "label": "Meeting host",
        "rule": "neuromancers_network.core.audience.is_meeting_host",
    },
    "meeting_seeker": {
        "label": "Meeting seeker",
        "rule": "neuromancers_network.core.audience.is_meeting_seeker",
    },
    "meeting_participant": {
        "label": "Meeting participant",
        "rule": "neuromancers_network.core.audience.is_meeting_participant",
    },
    "joining_meeting_host": {
        "label": "Joining an upcoming meeting (host)",
        "rule": (
            "neuromancers_network.core.audience.is_joining_upcoming_meeting_as_host"
        ),
    },
    "joining_meeting_guest": {
        "label": "Joining an upcoming meeting (guest)",
        "rule": (
            "neuromancers_network.core.audience.is_joining_upcoming_meeting_as_guest"
        ),
    },
    "own_profile": {
        "label": "Own profile",
        "rule": "neuromancers_network.core.audience.is_own_profile",
    },
    "own_profile_or_moderator": {
        "label": "Own profile or moderator",
        "rule": "neuromancers_network.core.audience.is_own_profile_or_moderator",
    },
    "bookmark_owner": {
        "label": "Bookmark owner",
        "rule": "neuromancers_network.core.audience.is_bookmark_owner",
    },
}
WAGTAIL_DAISIE_FORM_FIELD_TYPES = {
    "document": {
        "label": _("Document upload"),
        "field": "django.forms.FileField",
        "widget": "django.forms.ClearableFileInput",
        "css": "file-input w-full",
        "is_upload": True,
        "handler": "neuromancers_network.core.uploads.store_document",
    },
    "image": {
        "label": _("Image upload"),
        "field": "django.forms.ImageField",
        "widget": "django.forms.ClearableFileInput",
        "css": "file-input w-full",
        "is_upload": True,
        "handler": "neuromancers_network.users.avatar.store_image",
        "validators": ["neuromancers_network.core.validators.validate_image"],
    },
    "attachments": {
        "label": _("Attachments"),
        "display": "attachments",
        "multiple": True,
        "is_upload": True,
        "handler": "neuromancers_network.core.uploads.store_document",
    },
    "autocomplete": {
        "label": _("Autocomplete"),
        "field": "django.forms.MultipleChoiceField",
        "widget": "wagtail_daisIE.widgets.DaisieAutocompleteSelectMultiple",
        "choices": "neuromancers_network.taxonomy.selectors.tag_choices",
        "css": "select w-full",
    },
    "duration_tiers": {
        "label": _("Duration tiers"),
        "field": "neuromancers_network.meetings.tier_fields.DurationTiersField",
        "widget": "neuromancers_network.meetings.tier_fields.DurationTiersWidget",
    },
}
WAGTAIL_DAISIE_FORM_UPLOAD_HANDLER = "neuromancers_network.core.uploads.store_document"
WAGTAIL_DAISIE_APPROVAL_WORKFLOWS = {
    "peer_application": {
        "label": "Peer application",
        "model": "peers.PeerApplication",
        "approval_field": "is_approved",
        "handler": "neuromancers_network.peers.workflows.approve_peer_application",
    },
}
WAGTAIL_DAISIE_ACTIONS = {
    "meetings.create": {
        "label": _("Create meeting"),
        "handler": "neuromancers_network.meetings.actions.meetings_create",
    },
    "meetings.publish": {
        "label": _("Publish meeting"),
        "handler": "neuromancers_network.meetings.actions.meetings_publish",
    },
    "meetings.unpublish": {
        "label": _("Unpublish meeting"),
        "handler": "neuromancers_network.meetings.actions.meetings_unpublish",
    },
    "meetings.archive": {
        "label": _("Archive meeting"),
        "handler": "neuromancers_network.meetings.actions.meetings_archive",
    },
    "meetings.delete": {
        "label": _("Delete meeting"),
        "handler": "neuromancers_network.meetings.actions.meetings_delete",
    },
    "meetings.unpublish_all": {
        "label": _("Unpublish all meetings"),
        "handler": "neuromancers_network.meetings.actions.meetings_unpublish_all",
    },
    "meetings.delete_all": {
        "label": _("Delete all meetings"),
        "handler": "neuromancers_network.meetings.actions.meetings_delete_all",
    },
    "meetings.restore_default_terms": {
        "label": _("Restore default terms"),
        "handler": "neuromancers_network.meetings.actions.meetings_restore_default_terms",
    },
    "meetings.apply_terms_template": {
        "label": _("Apply terms template"),
        "handler": "neuromancers_network.meetings.actions.meetings_apply_terms_template",
    },
    "availability.create": {
        "label": _("Add availability"),
        "handler": "neuromancers_network.peers.actions.availability_create",
    },
    "availability.delete": {
        "label": _("Remove availability"),
        "handler": "neuromancers_network.peers.actions.availability_delete",
    },
    "bookings.checkout": {
        "label": _("Book and pay"),
        "handler": "neuromancers_network.meetings.actions.bookings_checkout",
    },
    "bookings.checkout_many": {
        "label": _("Pay for selected bookings"),
        "handler": "neuromancers_network.meetings.actions.bookings_checkout_many",
    },
    "bookings.approve": {
        "label": _("Approve booking"),
        "handler": "neuromancers_network.meetings.actions.bookings_approve",
    },
    "bookings.reject": {
        "label": _("Reject booking"),
        "handler": "neuromancers_network.meetings.actions.bookings_reject",
    },
    "bookings.revoke": {
        "label": _("Revoke booking"),
        "handler": "neuromancers_network.meetings.actions.bookings_revoke",
    },
    "refunds.approve": {
        "label": _("Approve refund"),
        "handler": "neuromancers_network.meetings.actions.refunds_approve",
    },
    "refunds.reject": {
        "label": _("Reject refund"),
        "handler": "neuromancers_network.meetings.actions.refunds_reject",
    },
    "review.approve": {
        "label": _("Approve review"),
        "handler": "neuromancers_network.meetings.actions.review_approve",
    },
    "review.hide": {
        "label": _("Hide review"),
        "handler": "neuromancers_network.meetings.actions.review_hide",
    },
    "bookings.request": {
        "label": _("Request booking"),
        "handler": "neuromancers_network.meetings.actions.bookings_request",
    },
    "bookings.request_refund": {
        "label": _("Request refund"),
        "handler": "neuromancers_network.meetings.actions.bookings_request_refund",
    },
    "peers.apply": {
        "label": _("Apply to be a care provider"),
        "handler": "neuromancers_network.peers.actions.peers_apply",
    },
    "peer.connect_stripe": {
        "label": _("Connect Stripe"),
        "handler": "neuromancers_network.peers.actions.peer_connect_stripe",
    },
    "peer.subscribe": {
        "label": _("Subscribe as a care provider"),
        "handler": "neuromancers_network.peers.actions.peer_subscribe",
    },
    "peer.subscription_pause": {
        "label": _("Pause plan"),
        "handler": "neuromancers_network.peers.actions.peer_subscription_pause",
    },
    "peer.subscription_resume": {
        "label": _("Resume plan"),
        "handler": "neuromancers_network.peers.actions.peer_subscription_resume",
    },
    "peer.subscription_cancel": {
        "label": _("Cancel plan"),
        "handler": "neuromancers_network.peers.actions.peer_subscription_cancel",
    },
    "peer.open_stripe_dashboard": {
        "label": _("Open Stripe dashboard"),
        "handler": "neuromancers_network.peers.actions.peer_open_stripe_dashboard",
    },
    "peer.accept_provider_agreement": {
        "label": _("Accept provider agreement"),
        "handler": "neuromancers_network.peers.actions.peer_accept_provider_agreement",
    },
    "peer.stripe_disconnect": {
        "label": _("Disconnect Stripe"),
        "handler": "neuromancers_network.peers.actions.peer_stripe_disconnect",
    },
    "profile.edit": {
        "label": _("Edit profile"),
        "handler": "neuromancers_network.users.actions.profile_edit",
    },
    "profile.save_access_needs": {
        "label": _("Save access needs"),
        "handler": "neuromancers_network.users.actions.profile_save_access_needs",
    },
    "profile.save_visibility": {
        "label": _("Save visibility"),
        "handler": "neuromancers_network.users.actions.profile_save_visibility",
    },
    "profile.save_notification_preferences": {
        "label": _("Save notification preferences"),
        "handler": "neuromancers_network.users.actions.profile_save_notification_preferences",
    },
    "accept_tos": {
        "label": _("Accept Terms and Conditions"),
        "handler": "neuromancers_network.users.actions.accept_tos",
    },
    "account.deactivate": {
        "label": _("Deactivate account"),
        "handler": "neuromancers_network.users.actions.account_deactivate",
    },
    "account.reactivate": {
        "label": _("Reactivate account"),
        "handler": "neuromancers_network.users.actions.account_reactivate",
    },
    "account.revoke_sessions": {
        "label": _("Sign out everywhere"),
        "handler": "neuromancers_network.users.actions.account_revoke_sessions",
    },
    "account.revoke_other_sessions": {
        "label": _("Sign out other devices"),
        "handler": "neuromancers_network.users.actions.account_revoke_other_sessions",
    },
    "calendar.revoke_token": {
        "label": _("Revoke calendar feed"),
        "handler": "neuromancers_network.core.actions.calendar_revoke_token",
    },
    "calendar.rotate_token": {
        "label": _("Rotate calendar feed"),
        "handler": "neuromancers_network.core.actions.calendar_rotate_token",
    },
    "account.delete_request": {
        "label": _("Delete my account"),
        "handler": "neuromancers_network.moderation.actions.account_delete_request",
    },
    "account.delete_cancel": {
        "label": _("Cancel account deletion"),
        "handler": "neuromancers_network.moderation.actions.account_delete_cancel",
    },
    "user.block": {
        "label": _("Block member"),
        "handler": "neuromancers_network.moderation.actions.user_block",
    },
    "user.unblock": {
        "label": _("Unblock member"),
        "handler": "neuromancers_network.moderation.actions.user_unblock",
    },
    "data.export_request": {
        "label": _("Request my data"),
        "handler": "neuromancers_network.moderation.actions.data_export_request",
    },
    # Settings-page sections (rendered by an app template override).
    "settings.account": {
        "label": _("Account settings"),
        "handler": "neuromancers_network.users.settings.action_handler",
    },
    "settings.profile": {
        "label": _("Profile settings"),
        "handler": "neuromancers_network.users.settings.action_handler",
    },
    "settings.privacy": {
        "label": _("Privacy settings"),
        "handler": "neuromancers_network.users.settings.action_handler",
    },
    "settings.notifications": {
        "label": _("Notification settings"),
        "handler": "neuromancers_network.users.settings.action_handler",
    },
    "notifications.mark_read": {
        "label": _("Mark notification read"),
        "handler": "neuromancers_network.inbox.actions.notifications_mark_read",
    },
    "notifications.mark_all_read": {
        "label": _("Mark all notifications read"),
        "handler": "neuromancers_network.inbox.actions.notifications_mark_all_read",
    },
    "notifications.delete": {
        "label": _("Delete notification"),
        "handler": "neuromancers_network.inbox.actions.notifications_delete",
    },
}
WAGTAIL_DAISIE_DETAIL_PAGES = {
    "meeting": {
        "label": "Meeting",
        "model": "meetings.Meeting",
        "page_type": "neuromancers_network.core.models.pages.MeetingDetailPage",
        "parent": "neuromancers_network.core.models.pages.MeetingIndexPage",
        "template_page": "neuromancers_network.core.models.pages.MeetingIndexPage",
        "lookup_field": "pk",
        "publish_field": "is_live",
        "title_source": "title",
        "slug_source": "title",
        "on_delete": "page",
    },
    "peer_profile": {
        "label": "Care provider",
        "model": "peers.PeerProfile",
        "page_type": "neuromancers_network.core.models.pages.PeerProfileDetailPage",
        "parent": "neuromancers_network.core.models.pages.PeerIndexPage",
        "template_page": "neuromancers_network.core.models.pages.PeerIndexPage",
        "lookup_field": "pk",
        "publish_field": "is_live",
        "title_source": "display_title",
        "slug_source": "username",
        "on_delete": "page",
    },
    "review": {
        "label": "Review",
        "model": "meetings.Review",
        "page_type": "neuromancers_network.core.models.pages.ReviewDetailPage",
        "parent": "neuromancers_network.core.models.pages.ReviewIndexPage",
        "template_page": "neuromancers_network.core.models.pages.ReviewIndexPage",
        "lookup_field": "pk",
        "publish_field": "is_live",
        "title_source": "display_title",
        "slug_source": "pk",
        "on_delete": "page",
    },
    "user_profile": {
        "label": "Member profile",
        "model": "users.User",
        "page_type": "neuromancers_network.core.models.pages.UserProfilePage",
        "parent": "neuromancers_network.core.models.pages.ProfileIndexPage",
        "template_page": "neuromancers_network.core.models.pages.ProfileIndexPage",
        "lookup_field": "username",
        "publish_field": "",
        "title_source": "display_name",
        "slug_source": "username",
        "on_delete": "page",
    },
    "booking": {
        "label": "Booking",
        "model": "meetings.Booking",
        "page_type": "neuromancers_network.core.models.pages.BookingDetailPage",
        "parent": "neuromancers_network.core.models.pages.HomePage",
        "template_page": (
            "neuromancers_network.core.models.pages.BookingDetailTemplate"
        ),
        "lookup_field": "pk",
        "publish_field": "",
        "title_source": "display_title",
        "slug_source": "pk",
        "on_delete": "page",
    },
    "refund_request": {
        "label": "Refund request",
        "model": "meetings.RefundRequest",
        "page_type": ("neuromancers_network.core.models.pages.RefundRequestDetailPage"),
        "parent": "neuromancers_network.core.models.pages.HomePage",
        "template_page": (
            "neuromancers_network.core.models.pages.RefundRequestDetailTemplate"
        ),
        "lookup_field": "pk",
        "publish_field": "",
        "title_source": "display_title",
        "slug_source": "pk",
        "on_delete": "page",
    },
    "tag": {
        "label": "Tag",
        "model": "taxonomy.AllowedTag",
        "page_type": "neuromancers_network.core.models.pages.TagDetailPage",
        "parent": "neuromancers_network.core.models.pages.TagIndexPage",
        "template_page": "neuromancers_network.core.models.pages.TagIndexPage",
        "lookup_field": "slug",
        "lookup_in": "path",
        "publish_field": "is_active",
        "title_source": "name",
        "slug_source": "slug",
        "on_delete": "page",
    },
}
# https://pypi.org/project/draftail-text-utils/
# Drive the Draftail editor's colour palette and font pickers from the default
# DaisyUI theme. COLORS uses a CALLABLE (daisIE exposes get_draftail_color_palette);
# FONT_FAMILIES/FONT_URLS use a MODULE because draftail_text_utils reads module-level
# list attributes, so core.draftail_palette lazily re-exports the daisIE font helpers.
DRAFTAIL_TEXT_UTILS = {
    "COLORS": {
        "CALLABLE": "wagtail_daisIE.utils.get_draftail_color_palette",
    },
    "FONT_FAMILIES": {
        "MODULE": "neuromancers_network.core.draftail_palette",
    },
    "FONT_URLS": {
        "MODULE": "neuromancers_network.core.draftail_palette",
    },
    # Let authors link text to a resolved context value (e.g. ``{{ user.url }}``);
    # daisIE feeds the editor's dynamic-link control and resolves them at render.
    "FEATURES": {"DYNAMIC_LINK": True},
}
