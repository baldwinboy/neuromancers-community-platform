from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.forms.models import model_to_dict
from django.test import override_settings
from wagtail.contrib.settings.views import get_setting_edit_handler
from wagtail.models.revisions import RevisionMixin

from neuromancers_network.core.checks import check_secret_decryption
from neuromancers_network.core.crypto import encrypt
from neuromancers_network.core.fields import EncryptedCharField
from neuromancers_network.core.fields import EncryptedTextField
from neuromancers_network.core.forms import StripeSettingsForm
from neuromancers_network.core.models import EmailSettings
from neuromancers_network.core.models import IntegrationSettings
from neuromancers_network.core.models import StripeSettings
from neuromancers_network.core.widgets import SecretInput

pytestmark = pytest.mark.django_db

SECRET = "sk_live_secret_123"  # noqa: S105


def _configured():
    config = StripeSettings.load()
    config.secret_key = SECRET
    config.save()
    return config


def _raw_secret(pk):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT secret_key FROM core_stripesettings WHERE id = %s",
            [pk],
        )
        return cursor.fetchone()[0]


class TestEncryptedFields:
    def test_round_trip_and_ciphertext_at_rest(self):
        config = _configured()

        raw = _raw_secret(config.pk)

        assert raw.startswith("enc:v1:")
        assert SECRET not in raw
        config.refresh_from_db()
        assert config.secret_key == SECRET

    def test_encrypt_is_idempotent(self):
        once = encrypt(SECRET)

        assert encrypt(once) == once

    def test_missing_key_fails_fast(self):
        with (
            override_settings(SECRET_KEY=""),
            pytest.raises(ImproperlyConfigured),
        ):
            encrypt("value")


class TestSecretInput:
    def test_shows_stored_status_without_revealing_value(self):
        widget = SecretInput(render_value=False)

        html = widget.render("secret", SECRET)

        assert "Stored — leave blank to keep" in html
        assert 'data-has-value="true"' in html
        assert SECRET not in html

    def test_shows_not_set_status(self):
        widget = SecretInput(render_value=False)

        html = widget.render("secret", "")

        assert "Not set" in html
        assert 'data-has-value="false"' in html

    def test_all_encrypted_fields_use_secret_input(self):
        for field_cls in (EncryptedCharField, EncryptedTextField):
            form_field = field_cls().formfield()

            assert isinstance(form_field.widget, SecretInput)


class TestSecretSettingsForm:
    def test_blank_value_keeps_the_existing_secret(self):
        config = _configured()
        data = model_to_dict(config)
        data["secret_key"] = ""

        form = StripeSettingsForm(data=data, instance=config)

        assert form.is_valid(), form.errors
        form.save()
        config.refresh_from_db()
        assert config.secret_key == SECRET

    def test_settings_forms_do_not_render_stored_secrets(self):
        stripe = _configured()

        email = EmailSettings.load()
        email.password = SECRET
        email.save()

        integration = IntegrationSettings.load()
        integration.whereby_api_key = SECRET
        integration.save()

        instances = (
            (StripeSettings, stripe),
            (EmailSettings, email),
            (IntegrationSettings, integration),
        )

        for model, instance in instances:
            form_class = get_setting_edit_handler(model).get_form_class()
            html = form_class(instance=instance).as_p()
            assert SECRET not in html
            assert 'data-has-value="true"' in html
            assert "Stored — leave blank to keep" in html

    def test_settings_are_not_revisioned(self):
        assert not issubclass(StripeSettings, RevisionMixin)


class TestSecretDecryptionCheck:
    def test_rotation_is_reported(self):
        _configured()

        with override_settings(SECRET_KEY="rotated-key"):  # noqa: S106
            errors = check_secret_decryption(None)

        assert any(error.id == "core.E001" for error in errors)
