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

# Render.com deployment settings
ALLOWED_HOSTS = (
    env("DJANGO_ALLOWED_HOSTS", default="")
    .split(", ")
    .append(
        "neuromancers-community-platform",
        ".localhost",
        "127.0.0.1",
        "[::1]",
        "*.neuromancers-community-platform.fly.dev",
        "*.ts.net",
    )
)

CSRF_TRUSTED_ORIGINS = [
    "https://neuromancers-community-platform.fly.dev",
    "https://*.ts.net",
]

# Support Render's external hostname
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


SECRET_KEY = env("DJANGO_SECRET_KEY")

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

# Security settings
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
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
