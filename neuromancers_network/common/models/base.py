import uuid

from django.db import models
from model_utils import FieldTracker


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tracker = FieldTracker()

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        editable=False,
    )

    class Meta:
        abstract = True
