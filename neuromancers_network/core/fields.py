"""Model fields that encrypt their value at rest."""

from __future__ import annotations

from django import forms
from django.db import models

from neuromancers_network.core.crypto import decrypt
from neuromancers_network.core.crypto import encrypt


class EncryptedTextField(models.TextField):
    """A text field whose database value is Fernet ciphertext."""

    def from_db_value(self, value, expression, connection):
        return decrypt(value)

    def to_python(self, value):
        return decrypt(value)

    def get_prep_value(self, value):
        return encrypt(super().get_prep_value(value))

    def formfield(self, **kwargs):
        kwargs.setdefault("widget", forms.PasswordInput(render_value=False))
        kwargs.setdefault("required", False)
        return super().formfield(**kwargs)


class EncryptedCharField(EncryptedTextField):
    """A secret string field (text-backed to fit the ciphertext)."""
