from __future__ import annotations

from django.urls import reverse
from wagtail.admin.menu import help_menu

from neuromancers_network.core.wagtail_hooks import HelpViewSetGroup

ADMIN_GUIDE_MENU_ORDER = 9000


def test_admin_guide_settings_menu_label():
    assert str(HelpViewSetGroup.menu_label) == "Admin Guide Settings"


def test_help_menu_links_to_the_admin_guide():
    items = {item.name: item for item in help_menu.registered_menu_items}

    settings_item = items["admin_help"]
    guide_item = items["admin_guide"]

    assert str(settings_item.label) == "Admin Guide Settings"
    assert guide_item.url == reverse("help_guide")
    assert guide_item.order == ADMIN_GUIDE_MENU_ORDER
