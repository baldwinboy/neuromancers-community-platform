import logging

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

from .models import EmailSettings

logger = logging.getLogger(__name__)

_DEFAULT_EMAIL_HOST = "localhost"
_DEFAULT_EMAIL_PORT = 25


class WagtailEmailBackend(SMTPBackend):
    """
    Email backend that reads SMTP configuration from the Wagtail
    settings model (core.models.EmailSettings).

    If the admin hasn't completed the configuration, sends fall back to the
    SMTP settings defined in settings.py. When neither is configured, messages
    are logged and dropped rather than attempting the Django default
    (localhost:25), so an unconfigured relay cannot break the request.
    """

    def __init__(self, fail_silently=False, **kwargs):  # noqa: FBT002
        # host, port, etc. are set in _load_runtime_settings() on each open().
        self._configured = False
        super().__init__(fail_silently=fail_silently, **kwargs)

    def send_messages(self, email_messages):
        self._load_runtime_settings()
        if not self._configured:
            logger.warning(
                "No SMTP email configuration available (EmailSettings inactive "
                "and no EMAIL_HOST override); dropping %d message(s).",
                len(email_messages),
            )
            return 0
        return super().send_messages(email_messages)

    def open(self):
        """Build a new connection every time - admin may have changed settings."""
        self._load_runtime_settings()
        return super().open()

    @staticmethod
    def _settings_configured() -> bool:
        return bool(
            getattr(settings, "EMAIL_HOST", _DEFAULT_EMAIL_HOST)
            not in ("", _DEFAULT_EMAIL_HOST)
            or getattr(settings, "EMAIL_PORT", _DEFAULT_EMAIL_PORT)
            != _DEFAULT_EMAIL_PORT
            or getattr(settings, "EMAIL_HOST_USER", ""),
        )

    def _load_runtime_settings(self):
        """Check the settings model and apply them to this backend instance."""
        self._configured = False
        try:
            email_settings = EmailSettings.load()
            if email_settings.is_active:
                self.host = email_settings.host
                self.port = email_settings.port
                self.username = email_settings.username
                self.password = email_settings.password
                self.use_tls = email_settings.use_tls
                self.use_ssl = email_settings.use_ssl
                self._configured = True
            elif self._settings_configured():
                self._configured = True
            if email_settings.default_from_email:
                self.from_email = email_settings.default_from_email
                self.default_from_email = email_settings.default_from_email
        except Exception:
            logger.exception(
                "Failed to load email settings from Wagtail admin.",
            )
