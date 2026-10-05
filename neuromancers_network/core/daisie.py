"""Single import point for ``wagtail_daisIE`` public objects.

Every daisIE model/adapter the project uses is re-exported here so application
code imports from one place. Importing this module does touch the app registry
(it imports models), so only import it from app code that runs after
``django.setup()``.
"""

from __future__ import annotations

from wagtail_daisIE.allauth_emails.allauth import DaisyUIAccountAdapterMixin
from wagtail_daisIE.allauth_emails.models import AllauthEmailOverride
from wagtail_daisIE.assets.models import DaisyUIIconSource
from wagtail_daisIE.errors.models import ErrorPage
from wagtail_daisIE.feeds.models import Feed
from wagtail_daisIE.menus.models import DaisyUIMenu
from wagtail_daisIE.models import DaisyUITheme
from wagtail_daisIE.notifications.models import Audience
from wagtail_daisIE.notifications.models import AudienceMember
from wagtail_daisIE.notifications.models import CampaignRecipientLog
from wagtail_daisIE.notifications.models import EmailCampaign
from wagtail_daisIE.notifications.models import EmailTemplate
from wagtail_daisIE.pages import StyledPageMixin

__all__ = [
    "AllauthEmailOverride",
    "Audience",
    "AudienceMember",
    "CampaignRecipientLog",
    "DaisyUIAccountAdapterMixin",
    "DaisyUIIconSource",
    "DaisyUIMenu",
    "DaisyUITheme",
    "EmailCampaign",
    "EmailTemplate",
    "ErrorPage",
    "Feed",
    "StyledPageMixin",
]
