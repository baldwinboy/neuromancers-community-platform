from __future__ import annotations

from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import TestCase

from neuromancers_network.common.binder import BinderError
from neuromancers_network.common.binder import ModelFormBinder
from neuromancers_network.events.models import Session
from neuromancers_network.events.models import SessionType

User = get_user_model()


def _make_request(user, post_data=None, files=None):
    rf = RequestFactory()
    method = "post" if post_data else "get"
    request = getattr(rf, method)("/", data=post_data or {}, files=files)
    request.user = user
    return request


def _binder(schema, request):
    return ModelFormBinder(schema, request)


class BinderCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_create_session(self):
        schema = {
            "model_target": "create_session",
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Session Title",
                        "model_field": "title",
                        "default_value": "",
                    },
                },
                {
                    "type": "dropdown_field",
                    "value": {
                        "field_label": "Session Type",
                        "model_field": "session_type",
                        "choices": ["peer"],
                    },
                },
            ],
        }
        request = _make_request(self.user, {"title": "My Session", "session_type": "peer"})
        result = _binder(schema, request).execute()

        assert result.success is True
        assert result.instance_id is not None
        session = Session.objects.get(pk=result.instance_id)
        assert session.title == "My Session"
        assert session.session_type == SessionType.PEER
        assert session.host == self.user

    def test_create_session_autofills_host(self):
        schema = {
            "model_target": "create_session",
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Title",
                        "model_field": "title",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(self.user, {"title": "Auto Host Test"})
        result = _binder(schema, request).execute()

        assert result.success is True
        session = Session.objects.get(pk=result.instance_id)
        assert session.host == self.user

    def test_create_session_model_validation_enforced(self):
        schema = {
            "model_target": "create_session",
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Title",
                        "model_field": "title",
                        "default_value": "",
                    },
                },
                {
                    "type": "number_field",
                    "value": {
                        "field_label": "Min Duration",
                        "model_field": "min_duration_minutes",
                        "default_value": "",
                    },
                },
                {
                    "type": "number_field",
                    "value": {
                        "field_label": "Max Duration",
                        "model_field": "max_duration_minutes",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(
            self.user,
            {"title": "Bad Session", "min_duration_minutes": 120, "max_duration_minutes": 30},
        )
        result = _binder(schema, request).execute()

        assert result.success is False

    def test_create_no_form_fields_returns_error(self):
        schema = {"model_target": "create_session", "form_fields": []}
        request = _make_request(self.user)
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "No form fields configured" in (result.non_field_errors or [])


class BinderUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.other = User.objects.create_user(
            username="other",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.session = Session.objects.create(
            host=self.user,
            title="Original Title",
            session_type=SessionType.PEER,
        )

    def test_update_session(self):
        schema = {
            "model_target": "edit_session",
            "target_object_id": str(self.session.id),
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Title",
                        "model_field": "title",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(self.user, {"title": "Updated Title"})
        result = _binder(schema, request).execute()

        assert result.success is True
        self.session.refresh_from_db()
        assert self.session.title == "Updated Title"

    def test_update_session_requires_target_id(self):
        schema = {
            "model_target": "edit_session",
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Title",
                        "model_field": "title",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(self.user, {"title": "No ID"})
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "target object ID" in (result.non_field_errors or [])[0].lower()

    def test_update_denied_for_non_owner(self):
        schema = {
            "model_target": "edit_session",
            "target_object_id": str(self.session.id),
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Title",
                        "model_field": "title",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(self.other, {"title": "Hacked Title"})
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "do not have permission" in (result.non_field_errors or [])[0].lower()

    def test_update_allowed_for_staff(self):
        staff = User.objects.create_user(
            username="staff",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
            is_staff=True,
        )
        schema = {
            "model_target": "edit_session",
            "target_object_id": str(self.session.id),
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Title",
                        "model_field": "title",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(staff, {"title": "Staff Updated"})
        result = _binder(schema, request).execute()

        assert result.success is True
        self.session.refresh_from_db()
        assert self.session.title == "Staff Updated"

    def test_update_nonexistent_session_returns_error(self):
        schema = {
            "model_target": "edit_session",
            "target_object_id": "00000000-0000-0000-0000-000000000000",
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Title",
                        "model_field": "title",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(self.user, {"title": "Ghost"})
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "not found" in (result.non_field_errors or [])[0].lower()


class BinderDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.other = User.objects.create_user(
            username="other",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.session = Session.objects.create(
            host=self.user,
            title="Delete Me",
            session_type=SessionType.PEER,
        )

    def test_delete_session_with_confirmation(self):
        schema = {
            "model_target": "delete_session",
            "target_object_id": str(self.session.id),
            "form_fields": [],
        }
        request = _make_request(self.user, {"confirm": "on"})
        result = _binder(schema, request).execute()

        assert result.success is True
        assert result.instance_id == str(self.session.id)
        assert not Session.objects.filter(pk=self.session.pk).exists()

    def test_delete_without_confirmation_fails(self):
        schema = {
            "model_target": "delete_session",
            "target_object_id": str(self.session.id),
            "form_fields": [],
        }
        request = _make_request(self.user, {})
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "not confirmed" in (result.non_field_errors or [])[0].lower()
        assert Session.objects.filter(pk=self.session.pk).exists()

    def test_delete_denied_for_non_owner(self):
        schema = {
            "model_target": "delete_session",
            "target_object_id": str(self.session.id),
            "form_fields": [],
        }
        request = _make_request(self.other, {"confirm": "on"})
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "do not have permission" in (result.non_field_errors or [])[0].lower()
        assert Session.objects.filter(pk=self.session.pk).exists()

    def test_delete_allowed_for_staff(self):
        staff = User.objects.create_user(
            username="staff",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
            is_staff=True,
        )
        schema = {
            "model_target": "delete_session",
            "target_object_id": str(self.session.id),
            "form_fields": [],
        }
        request = _make_request(staff, {"confirm": "on"})
        result = _binder(schema, request).execute()

        assert result.success is True
        assert not Session.objects.filter(pk=self.session.pk).exists()


class BinderPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_unknown_model_target(self):
        schema = {"model_target": "nonexistent", "form_fields": []}
        request = _make_request(self.user)
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "unknown" in (result.non_field_errors or [])[0].lower()

    def test_blocked_field_rejected(self):
        schema = {
            "model_target": "create_session",
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Status",
                        "model_field": "booking_status",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(self.user, {"status": "confirmed"})
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "blocked" in (result.non_field_errors or [])[0].lower()

    def test_allowlist_violation_rejected(self):
        schema = {
            "model_target": "create_session",
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Secret",
                        "model_field": "host",
                        "default_value": "",
                    },
                },
            ],
        }
        request = _make_request(self.user, {"secret": str(self.user.id)})
        result = _binder(schema, request).execute()

        assert result.success is False
        assert "allowlist" in (result.non_field_errors or [])[0].lower()


class BinderNoModelTests(TestCase):
    def test_no_model_form_succeeds(self):
        schema = {
            "model_target": "",
            "form_fields": [
                {
                    "type": "char_field",
                    "value": {
                        "field_label": "Message",
                        "model_field": "",
                        "default_value": "",
                    },
                },
            ],
        }
        user = User.objects.create_user(
            username="guest",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        request = _make_request(user, {"message": "Hello"})
        result = _binder(schema, request).execute()

        assert result.success is True
        assert result.instance is None
