import os
import re

import dj_database_url

from .base import *
from .bots import bots

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    ENVIRONMENT=(str, "production"),
)

# Build ALLOWED_HOSTS from env var + static entries
_allowed_hosts_env = env("DJANGO_ALLOWED_HOSTS", default="")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(",") if h.strip()]

# Add static allowed hosts
ALLOWED_HOSTS += [
    "neuromancers-community-platform",  # Tailscale MagicDNS hostname
    ".ts.net",  # Tailscale domain suffix (matches any subdomain)
    "localhost",
    "127.0.0.1",
    "[::1]",
]

CSRF_TRUSTED_ORIGINS = [
    "https://*.ts.net",  # Tailscale HTTPS via MagicDNS FQDN
    "http://neuromancers-community-platform:8000",  # Fallback HTTP
]

# Support Render's external hostname (if deploying there)
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


SECRET_KEY = env("DJANGO_SECRET_KEY") or env("SECRET_KEY")

ENVIRONMENT = env("ENVIRONMENT")

DATABASE_URL = env(
    "DATABASE_URL", default="postgresql://postgres:postgres@localhost:5432/neuromancers"
)

DEBUG = env("DEBUG")

# Database - use DATABASE_URL from Render PostgreSQL
DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
    )
}

IGNORABLE_404_URLS = [
    re.compile(r"^/cpc/"),
    re.compile(r"^/cpanel/"),
    re.compile(r"^/favicon\.ico$"),
    re.compile(r"^/robots\.txt$"),
    re.compile(r"\.(cgi|php|pl)$"),
    re.compile(r"^/apple-touch-icon.*\.png$"),
]

DISALLOWED_USER_AGENTS = bots

# Security settings for Tailscale HTTPS
# Secure cookies enabled by default for HTTPS
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)

# SSL redirect - disabled since gunicorn serves HTTPS directly (no proxy)
# Only enable if using a reverse proxy that terminates SSL
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

ACCOUNT_EMAIL_NOTIFICATIONS = True
ACCOUNT_CHANGE_EMAIL = True

EMAIL_USE_TLS = True
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# WhiteNoise for static file serving on Render
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

# Static files storage with WhiteNoise compression
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Wagtail admin URL for production
WAGTAILADMIN_BASE_URL = env("WAGTAILADMIN_BASE_URL", default="")

try:
    from .local import *
except ImportError:
    pass
