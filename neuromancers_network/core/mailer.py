import logging

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

from .models import EmailSettings


class WagtailEmailBackend(SMTPBackend):
    """
    Email backend that reads SMTP configuration from the Wagtail
    SiteSettings model (core.models.EmailSettings).

    If the admin hasn't completed the configuration, every send()
    call falls back to the standard Django SMTP backend defined in
    settings.py.
    """

    def __init__(self, fail_silently=False, **kwargs):  # noqa: FBT002
        # We'll set host, port, etc. inside _get_runtime_settings()
        super().__init__(fail_silently=fail_silently, **kwargs)

    def open(self):
        """Build a new connection every time — admin may have changed settings."""
        self._load_runtime_settings()
        return super().open()

    def _load_runtime_settings(self):
        """Check the SiteSettings and apply them to this backend instance."""
        try:
            settings = EmailSettings.load()
            if settings.is_active:
                self.host = settings.host
                self.port = settings.port
                self.username = settings.username
                self.password = settings.password
                self.use_tls = settings.use_tls
                self.use_ssl = settings.use_ssl
        except Exception:
            logging.exception(
                "Failed to load email settings from Wagtail admin.")
