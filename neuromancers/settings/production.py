import os
import re

from .base import *
from .bots import bots

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    ENVIRONMENT=(str, "production"),
)

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "").split(", ")

SECRET_KEY = env("DJANGO_SECRET_KEY")

ENVIRONMENT = env("ENVIRONMENT")

DEBUG = env("DEBUG")

STATICFILES_FINDERS.append("compressor.finders.CompressorFinder")

IGNORABLE_404_URLS = [
    re.compile(r"^/cpc/"),
    re.compile(r"^/cpanel/"),
    re.compile(r"^/favicon\.ico$"),
    re.compile(r"^/robots\.txt$"),
    re.compile(r"\.(cgi|php|pl)$"),
    re.compile(r"^/apple-touch-icon.*\.png$"),
]

DISALLOWED_USER_AGENTS = bots

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SECURE = True

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

try:
    from .local import *
except ImportError:
    pass
