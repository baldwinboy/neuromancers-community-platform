"""
WSGI config for neuromancers project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Select settings module based on ENVIRONMENT variable
environment = os.environ.get("ENVIRONMENT", "development")
if environment == "production":
    settings_module = "neuromancers.settings.production"
else:
    settings_module = "neuromancers.settings.dev"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

application = get_wsgi_application()
