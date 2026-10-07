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
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
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
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
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
# Admin-authored arbitrary CSS.
MIDDLEWARE.append("wagtail_daisIE.middleware.ArbitraryCSSMiddleware")

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
    "name*",
    "date_of_birth*",
    "email*",
    "email2*",
    "password1*",
    "password2*",
    "accept_toc*",
]
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_ADAPTER = "neuromancers_network.users.adapters.AccountAdapter"
# https://docs.allauth.org/en/latest/account/forms.html
ACCOUNT_FORMS = {"signup": "neuromancers_network.users.forms.UserSignupForm"}

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
# Render allauth pages (login/signup/etc.) with the DaisyUI theme overrides.
WAGTAIL_DAISIE_ALLAUTH_UI = True
# Chrome used to render allauth pages (read by wagtail_daisIE >= 2.0.0).
WAGTAIL_DAISIE_ALLAUTH_BASE_TEMPLATE = "base.html"
WAGTAIL_DAISIE_HEADER_MENU = "Main navigation"
WAGTAIL_DAISIE_FOOTER_MENU = "Footer"
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
        "lookup_field": "pk",
        "queryset": "neuromancers_network.meetings.selectors.published_meetings",
        "select_related": ["peer"],
    },
    "peer_profile": {
        "label": _("Care provider"),
        "model": "peers.PeerProfile",
        "source": "url",
        "lookup_field": "pk",
        "queryset": "neuromancers_network.peers.selectors.approved_peers",
        "select_related": ["user"],
    },
    "review": {
        "label": _("Review"),
        "model": "meetings.Review",
        "source": "url",
        "lookup_field": "pk",
        "queryset": "neuromancers_network.meetings.selectors.published_reviews",
    },
    "user_profile": {
        "label": _("Member profile"),
        "model": "users.UserProfile",
        "source": "url",
        "lookup_field": "user_id",
    },
    "booking": {
        "label": _("Booking"),
        "model": "meetings.Booking",
        "source": "url",
        "lookup_field": "pk",
        "queryset": "neuromancers_network.meetings.selectors.user_bookings",
        "select_related": ["meeting"],
    },
    "peer_application": {
        "label": _("Peer application"),
        "model": "peers.PeerApplication",
        "source": "url",
        "lookup_field": "user_id",
    },
    "refund_request": {
        "label": _("Refund request"),
        "model": "meetings.RefundRequest",
        "source": "url",
        "lookup_field": "pk",
    },
    "notification_preference": {
        "label": _("Notification preferences"),
        "model": "inbox.NotificationPreference",
        "source": "neuromancers_network.inbox.selectors.user_notification_preference",
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
    "subscription_created",
    "subscription_cancelled",
    "payment_succeeded",
    "payment_failed",
    "payment_reminder_due",
    "meeting_upcoming",
    "meeting_cancelled",
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
    },
    "peer": {
        "label": "Care providers",
        "rule": "neuromancers_network.core.audience.is_peer",
    },
    "verified_peer": {
        "label": "Verified care providers",
        "rule": "neuromancers_network.core.audience.is_verified_peer",
    },
    "moderator": {
        "label": "Moderators",
        "rule": "neuromancers_network.core.audience.is_moderator",
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
    "meetings.restore_default_terms": {
        "label": _("Restore default terms"),
        "handler": "neuromancers_network.meetings.actions.meetings_restore_default_terms",
    },
    "bookings.checkout": {
        "label": _("Book and pay"),
        "handler": "neuromancers_network.meetings.actions.bookings_checkout",
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
    "peer.open_stripe_dashboard": {
        "label": _("Open Stripe dashboard"),
        "handler": "neuromancers_network.peers.actions.peer_open_stripe_dashboard",
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
        "on_delete": "unlink",
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
        "on_delete": "unlink",
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
        "on_delete": "unlink",
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
        "on_delete": "unlink",
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
