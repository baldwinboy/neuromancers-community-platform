from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import cache
from typing import Any

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models as db_models
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from neuromancers_network.common.blocks.modelform_fields import MODEL_ACTION_MAP

logger = logging.getLogger(__name__)

AUTOFILL_MAP: dict[str, str] = {
    "host": "user",
    "owner": "user",
    "user": "user",
}

BLOCKED_FIELDS: set[str] = {
    "id",
    "pk",
    "created_at",
    "updated_at",
    "booking_status",
    "payment_status",
    "stripe_account",
}

MODEL_ALLOWLISTS: dict[str, set[str]] = {
    "events.session": {
        "title",
        "description",
        "session_type",
        "languages",
        "visibility",
        "is_published",
        "capacity",
        "min_duration_minutes",
        "max_duration_minutes",
        "tos_text",
        "require_approval",
        "require_refund_approval",
        "require_payment_before_joining",
        "meeting_link",
        "category",
        "starts_at",
        "ends_at",
        "currency",
    },
    "users.profile": {
        "bio",
        "languages",
        "notification_prefs",
    },
}

OWNERSHIP_MAP: dict[str, str] = {
    "events.session": "host",
    "users.profile": "user",
}


class BinderError(Exception):
    """Raised when the binder encounters a configuration or execution error."""


@dataclass
class BinderResult:
    success: bool
    instance: Any = None
    instance_id: str | None = None
    field_errors: dict[str, list[str]] | None = None
    non_field_errors: list[str] | None = None


class ModelFormBinder:
    def __init__(self, block_schema: dict, request):
        self.block_schema = block_schema
        self.request = request
        self.user = request.user
        self._field_map: dict[str, str] = {}

    def execute(self) -> BinderResult:
        try:
            model_label, action = self._resolve_action()

            if not model_label:
                return self._handle_no_model()

            model_class = self._get_model_class(model_label)
            instance = self._get_or_create_instance(model_class, action)

            if action == "delete":
                return self._execute_delete(instance, model_class)

            runtime_form = self._build_runtime_form(model_class)
            if not runtime_form:
                return BinderResult(success=False, non_field_errors=["No form fields configured."])

            form = runtime_form(self.request.POST or None, self.request.FILES or None)
            if not form.is_valid():
                return BinderResult(
                    success=False,
                    field_errors=dict(form.errors),
                )

            with transaction.atomic():
                self._check_ownership(instance, model_class, action)
                self._map_fields(instance, form, model_class)
                self._autofill(instance, action)
                instance.full_clean()
                instance.save()
                self._execute_post_save(instance, action)

            return BinderResult(
                success=True,
                instance=instance,
                instance_id=str(instance.pk),
            )

        except BinderError as e:
            return BinderResult(success=False, non_field_errors=[str(e)])
        except ValidationError as e:
            return BinderResult(
                success=False,
                non_field_errors=e.messages if hasattr(e, "messages") else [str(e)],
            )

    def _execute_delete(self, instance, model_class) -> BinderResult:
        runtime_form = self._build_runtime_form(model_class)
        if runtime_form:
            form = runtime_form(self.request.POST or None, self.request.FILES or None)
            if not form.is_valid():
                return BinderResult(success=False, field_errors=dict(form.errors))

        self._check_ownership(instance, model_class, "delete")

        confirm = self.request.POST.get("confirm") == "on"
        if not confirm:
            return BinderResult(success=False, non_field_errors=["Deletion not confirmed."])

        with transaction.atomic():
            instance_id = str(instance.pk)
            instance.delete()
            logger.info(
                "Deleted %s %s by user %s",
                model_class._meta.label,
                instance_id,
                self.user,
            )

        return BinderResult(success=True, instance_id=instance_id)

    def _check_ownership(self, instance, model_class, action):
        if action == "create":
            return
        owner_field = OWNERSHIP_MAP.get(model_class._meta.label)
        if not owner_field:
            return
        owner = getattr(instance, owner_field, None)
        if owner is not None and owner != self.user and not self.user.is_staff:
            raise BinderError(
                f"You do not have permission to {action} this {model_class._meta.model_name}."
            )

    def _handle_no_model(self):
        runtime_form = self._build_runtime_form(None)
        if runtime_form:
            form = runtime_form(self.request.POST or None, self.request.FILES or None)
            if not form.is_valid():
                return BinderResult(success=False, field_errors=dict(form.errors))
        logger.info("No-model form submitted by user %s", self.user)
        return BinderResult(success=True)

    def _resolve_action(self) -> tuple[str | None, str | None]:
        model_target = self.block_schema.get("model_target")
        if not model_target:
            return None, None
        action_info = MODEL_ACTION_MAP.get(model_target)
        if not action_info:
            raise BinderError(f"Unknown model target: {model_target}")
        return action_info["model"], action_info["action"]

    def _get_model_class(self, model_label: str):
        try:
            app_label, model_name = model_label.split(".")
            return apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as e:
            raise BinderError(f"Invalid model: {model_label}") from e

    def _get_or_create_instance(self, model_class, action):
        if action == "create":
            return model_class()
        instance_id = self.block_schema.get("target_object_id")
        if not instance_id:
            raise BinderError("Update or delete requires a target object ID.")
        try:
            return model_class.objects.get(pk=instance_id)
        except model_class.DoesNotExist:
            raise BinderError("Target object not found.")

    def _build_runtime_form(self, model_class):
        field_defs = self.block_schema.get("form_fields", [])
        if not field_defs:
            return None

        attrs = {}
        self._field_map = {}
        allowed_fields = MODEL_ALLOWLISTS.get(model_class._meta.label, set()) if model_class else set()

        for block_data in field_defs:
            block_type = block_data.get("type")
            value = block_data.get("value", {})
            model_field = value.get("model_field", "")

            if model_field and model_class:
                if model_field in BLOCKED_FIELDS:
                    raise BinderError(f"Field '{model_field}' is blocked and cannot be mapped.")
                if model_field not in allowed_fields:
                    raise BinderError(
                        f"Field '{model_field}' is not in the allowlist for {model_class._meta.label}."
                    )

            slug = self._get_block_slug(block_type, value)
            if not slug:
                continue

            field = self._build_django_field(block_type, value)
            if field is None:
                continue

            attrs[slug] = field
            if model_field:
                self._field_map[slug] = model_field

        if not attrs:
            return None
        return type("RuntimeForm", (forms.Form,), attrs)

    def _get_block_slug(self, block_type, value):
        block = self._get_block_class(block_type)
        if block and hasattr(block, "get_slug"):
            return block().get_slug(value)
        return None

    @cache
    def _get_block_class(self, block_type):
        from neuromancers_network.common.blocks.modelform_fields import ModelFormFieldsBlock

        child_blocks = ModelFormFieldsBlock().child_blocks
        return child_blocks.get(block_type)

    def _build_django_field(self, block_type, value):
        block = self._get_block_class(block_type)
        if block and hasattr(block, "get_field"):
            try:
                return block().get_field(value)
            except Exception:
                return None
        return None

    def _map_fields(self, instance, form, model_class):
        allowed_fields = MODEL_ALLOWLISTS.get(model_class._meta.label, set())
        for slug, model_field in self._field_map.items():
            if model_field not in allowed_fields or model_field in BLOCKED_FIELDS:
                continue
            cleaned_value = form.cleaned_data.get(slug)
            cleaned_value = self._coerce_json(model_class, model_field, cleaned_value)
            setattr(instance, model_field, cleaned_value)

    def _coerce_json(self, model_class, model_field, value):
        try:
            field = model_class._meta.get_field(model_field)
            if isinstance(field, db_models.JSONField) and isinstance(value, str):
                return json.loads(value)
        except db_models.FieldDoesNotExist:
            pass
        return value

    def _autofill(self, instance, action):
        if action == "create":
            for model_field, source in AUTOFILL_MAP.items():
                if hasattr(instance, model_field):
                    if source == "user":
                        setattr(instance, model_field, self.user)

    def _execute_post_save(self, instance, action):
        pass
