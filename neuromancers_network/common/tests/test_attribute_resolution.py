from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.template import Context
from django.template import Template
from django.test import TestCase

from neuromancers_network.common.templatetags.content_blocks import _resolve_attribute
from neuromancers_network.common.templatetags.content_blocks import _resolve_candidate

User = get_user_model()


def _context_with(user=None, page=None, object_=None):
    ctx = {"request": type("Req", (), {"user": user})() if user else None}
    if page:
        ctx["page"] = page
    if object_:
        ctx["object"] = object_
    if user:
        ctx["user"] = user
    return ctx


class ResolveCandidateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="seeker",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_resolves_user_from_context(self):
        ctx = _context_with(user=self.user)
        candidate = _resolve_candidate(ctx, "users.user")
        assert candidate == self.user

    def test_returns_none_for_missing_model(self):
        ctx = _context_with(user=self.user)
        candidate = _resolve_candidate(ctx, "nonexistent.model")
        assert candidate is None

    def test_resolves_object_over_user(self):
        class DummyPage:
            _meta = type("Meta", (), {"label": "users.user"})()

        dummy = DummyPage()
        ctx = _context_with(user=self.user, object_=dummy)
        candidate = _resolve_candidate(ctx, "users.user")
        assert candidate == dummy

    def test_resolves_explicit_context_object(self):
        explicit = User.objects.create_user(
            username="explicit",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        ctx = _context_with(user=self.user)
        ctx["context_objects"] = {"users.user": explicit}
        candidate = _resolve_candidate(ctx, "users.user")
        assert candidate == explicit


class ResolveAttributeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_direct_attribute(self):
        result = _resolve_attribute(self.user, "username")
        assert result == "testuser"

    def test_dotted_path_attribute(self):
        result = _resolve_attribute(self.user, "username")
        assert result == "testuser"

    def test_none_attribute_returns_empty(self):
        result = _resolve_attribute(self.user, "nonexistent_field")
        assert result == ""

    def test_callable_attribute(self):
        result = _resolve_attribute(self.user, "get_absolute_url")
        assert result == self.user.get_absolute_url()


class AttributeValueTagTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="taguser",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def _render(self, context, model, model_field):
        t = Template(
            "{% load content_blocks %}"
            '{% attribute_value {"model": "'
            + model
            + '", "model_field": "'
            + model_field
            + '"} as val %}{{ val }}'
        )
        return t.render(Context(context))

    def test_tag_resolves_username(self):
        ctx = _context_with(user=self.user)
        result = self._render(ctx, "users.user", "username")
        assert result == "taguser"

    def test_tag_returns_empty_for_missing_model(self):
        ctx = _context_with(user=self.user)
        result = self._render(ctx, "users.user", "nonexistent")
        assert result == ""

    def test_tag_returns_empty_for_missing_model_label(self):
        ctx = _context_with(user=self.user)
        result = self._render(ctx, "nonexistent.model", "username")
        assert result == ""
