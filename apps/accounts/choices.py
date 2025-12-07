from django.db import models
from django.utils.translation import gettext as _

class NotificationChoices(models.IntegerChoices):
    """
    Notifications may sent on the platform, via email, or not at all
    """

    NONE = 0, _("None")
    WEB_ONLY = 1, _("On this site")
    EMAIL = 2, _("Via email")
    ALL = 3, _("All")
