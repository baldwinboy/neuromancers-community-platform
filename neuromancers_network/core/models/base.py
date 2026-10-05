from django.db import models
from django.utils.translation import gettext_lazy as _


class Timestamped(models.Model):
    """
    Abstract base class for models that have a created_at and updated_at field.
    """

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        abstract = True
