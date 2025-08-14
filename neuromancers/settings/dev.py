from .base import *

INSTALLED_APPS.append("debug_toolbar")

MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

INTERNAL_IPS = ["127.0.0.1"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-9!f@(p-gs3re&zi)mw&)iy4r3e#7mp^mcipclyr8+pubujymvm"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

try:
    from .local import *
except ImportError:
    pass
