"""Shared Wagtail admin viewset mixins."""

from __future__ import annotations


class HiddenFromSnippetIndexMixin:
    """Snippet-registered but omitted from the generic Snippets index/menu.

    Bulk actions are native to ``SnippetViewSet``. Registering through one keeps
    those actions, but the model should stay out of the generic "Snippets" index
    (it lives in its own admin submenu). ``SnippetViewSet`` and
    ``SnippetViewSetGroup`` assign ``menu_item_is_registered`` as an *attribute*,
    and groups clobber it, so override the **method** instead.
    """

    def get_menu_item_is_registered(self):
        return True
