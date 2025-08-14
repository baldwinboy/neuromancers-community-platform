import os

from .base import *

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(", ")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")

ENVIRONMENT = "production"

DEBUG = False

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

try:
    from .local import *
except ImportError:
    pass
