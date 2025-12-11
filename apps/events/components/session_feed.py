from wagtail.admin.ui.components import Component

from apps.events.models_sessions.group import GroupSession
from apps.events.models_sessions.peer import PeerSession


class SessionFeed(Component):
    template_name = "includes/session_feed.html"

    def __init__(self, block_value):
        super().__init__()
        self.block_value = block_value

    def get_context_data(self, parent_context=None):
        ctx = super().get_context_data(parent_context).copy()
        limit = self.block_value.get("limit", 10)
        half = max(limit // 2, 1)

        # Fetch ORM objects (DB is still open here)
        peer = list(
            PeerSession.objects.filter(is_published=True)
            .select_related("host")
            .order_by("-created_at")[:half]
        )

        group = list(
            GroupSession.objects.filter(is_published=True)
            .select_related("host", "page")
            .order_by("-created_at")[:half]
        )

        # Merge
        merged = peer + group
        merged.sort(key=lambda x: x.created_at, reverse=True)
        merged = merged[:limit]

        # Convert EVERYTHING to basic data types
        safe_items = []

        for s in merged:
            # Precompute URL safely (while DB open)
            url = "#"
            page = getattr(s, "page", None)
            if page:
                try:
                    url = page.url
                except Exception:
                    pass

            # Copy ONLY safe fields
            safe_items.append(
                {
                    "id": str(s.id),
                    "title": s.title,
                    "starts_at": getattr(s, "starts_at", None),
                    "created_at": s.created_at,
                    "host": str(s.host),
                    "url": url,
                    "type": "group" if hasattr(s, "starts_at") else "peer",
                }
            )

        # Store only primitives in context
        ctx["sessions"] = safe_items
        ctx["paginator"] = None
        return ctx
