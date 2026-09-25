import logging

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

from .models import EmailSettings


class WagtailEmailBackend(SMTPBackend):
    """
    Email backend that reads SMTP configuration from the Wagtail
    settings model (core.models.EmailSettings).

    If the admin hasn't completed the configuration, every send()
    call falls back to the SMTP settings defined in settings.py.
    """

    def __init__(self, fail_silently=False, **kwargs):  # noqa: FBT002
        # host, port, etc. are set in _load_runtime_settings() on each open().
        super().__init__(fail_silently=fail_silently, **kwargs)

    def open(self):
        """Build a new connection every time - admin may have changed settings."""
        self._load_runtime_settings()
        return super().open()

    def _load_runtime_settings(self):
        """Check the settings model and apply them to this backend instance."""
        try:
            email_settings = EmailSettings.load()
            if email_settings.is_active:
                self.host = email_settings.host
                self.port = email_settings.port
                self.username = email_settings.username
                self.password = email_settings.password
                self.use_tls = email_settings.use_tls
                self.use_ssl = email_settings.use_ssl
            if email_settings.default_from_email:
                self.from_email = email_settings.default_from_email
                self.default_from_email = email_settings.default_from_email
        except Exception:
            logging.exception(
                "Failed to load email settings from Wagtail admin.",
            )
