from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Exists, F, OuterRef, Q
from django.utils import timezone
from wagtail.admin.ui.components import Component
from wagtail.contrib.settings.registry import registry

from apps.events.choices import SessionRequestStatusChoices
from apps.events.models_sessions.group import GroupSession, GroupSessionRequest
from apps.events.models_sessions.peer import (
    PeerSession,
    PeerSessionAvailability,
    PeerSessionRequest,
)
from apps.events.utils import parse_csv_string

# Build language lookup dict from settings
LANGUAGE_MAP = {code: name for code, name in settings.LANGUAGES}


def get_filter_settings():
    """Load FilterSettings and return normalized mapping."""
    try:
        filter_settings = registry.get_by_natural_key("events", "FilterSettings").load()
        return filter_settings.get_cached_mapping()
    except Exception:
        return {}


def get_available_languages():
    """
    Get languages that are actually used by published sessions.
    Returns a dict of {code: name} for languages in use.
    """
    # Get languages from peer sessions (comma-separated)
    peer_languages = (
        PeerSession.objects.filter(is_published=True)
        .exclude(languages__isnull=True)
        .exclude(languages="")
        .values_list("languages", flat=True)
    )

    # Parse comma-separated peer session languages
    language_codes = set()
    for lang_str in peer_languages:
        if lang_str:
            language_codes.update(parse_csv_string(lang_str))

    # Get languages from group sessions (single value)
    group_languages = (
        GroupSession.objects.filter(is_published=True)
        .exclude(language__isnull=True)
        .exclude(language="")
        .values_list("language", flat=True)
        .distinct()
    )
    language_codes.update(group_languages)

    # Map to display names
    return {code: LANGUAGE_MAP.get(code, code) for code in sorted(language_codes)}


class SessionFeed(Component):
    template_name = "includes/session_feed.html"

    def __init__(self, block_value):
        super().__init__()
        self.block_value = block_value

    def get_context_data(self, parent_context=None):
        ctx = super().get_context_data(parent_context).copy()
        limit = self.block_value.get("limit", 10)
        show_filters = self.block_value.get("show_filters", False)
        enable_pagination = self.block_value.get("enable_pagination", False)

        # Get default values from block config
        include_peer = self.block_value.get("include_peer_sessions", True)
        include_group = self.block_value.get("include_group_sessions", True)
        include_unavailable = self.block_value.get("include_unavailable", False)
        include_full_capacity = self.block_value.get("include_full_capacity", False)
        sort_order = "newest"

        # Load filter settings categories and available languages
        filter_categories = get_filter_settings() if show_filters else {}
        available_languages = get_available_languages() if show_filters else {}
        selected_filters = {}  # Track which category filters are selected
        selected_languages = []  # Track selected language filters

        # If filters are shown, allow user to override via request params
        request = parent_context.get("request") if parent_context else None
        current_page = 1
        if show_filters and request:
            # Check if any filter params are present
            if "include_peer" in request.GET:
                include_peer = request.GET.get("include_peer") == "1"
            if "include_group" in request.GET:
                include_group = request.GET.get("include_group") == "1"
            if "include_unavailable" in request.GET:
                include_unavailable = request.GET.get("include_unavailable") == "1"
            if "include_full" in request.GET:
                include_full_capacity = request.GET.get("include_full") == "1"
            if "sort" in request.GET:
                sort_order = request.GET.get("sort", "newest")

            # Language filter (comma-separated)
            if "languages" in request.GET:
                lang_param = request.GET.get("languages", "")
                selected_languages = [
                    v.strip() for v in lang_param.split(",") if v.strip()
                ]

            # Parse category filter selections (e.g., ?filter_lived-experience=black,lgbt)
            for group_slug in filter_categories.keys():
                param_name = f"filter_{group_slug}"
                if param_name in request.GET:
                    values = request.GET.get(param_name, "").split(",")
                    selected_filters[group_slug] = [
                        v.strip() for v in values if v.strip()
                    ]

        if enable_pagination and request:
            try:
                current_page = int(request.GET.get("page", 1))
            except (ValueError, TypeError):
                current_page = 1

        now = timezone.now()
        half = max(limit // 2, 1)

        peer = []
        group = []

        # Fetch Peer sessions
        if include_peer:
            peer_qs = PeerSession.objects.filter(is_published=True).select_related(
                "host"
            )

            if not include_unavailable:
                # Only include peer sessions that have availability
                has_availability = Exists(
                    PeerSessionAvailability.objects.filter(
                        session=OuterRef("pk")
                    ).filter(
                        Q(starts_at__gte=now)
                        | Q(occurrence__isnull=False, occurrence_ends_at__isnull=True)
                        | Q(occurrence__isnull=False, occurrence_ends_at__gte=now)
                    )
                )
                peer_qs = peer_qs.filter(has_availability)

            # Apply language filter to peer sessions (comma-separated field)
            if selected_languages:
                lang_q = Q()
                for lang_code in selected_languages:
                    lang_q |= Q(languages__icontains=lang_code)
                peer_qs = peer_qs.filter(lang_q)

            peer = list(peer_qs.order_by("-created_at")[:half])

        # Fetch Group sessions
        if include_group:
            group_qs = GroupSession.objects.filter(
                is_published=True, starts_at__gte=now
            ).select_related("host", "page")

            if not include_full_capacity:
                # Annotate with approved attendee count and filter
                group_qs = group_qs.annotate(
                    approved_count=Count(
                        "requests",
                        filter=Q(requests__status=SessionRequestStatusChoices.APPROVED),
                    )
                ).filter(capacity__gt=F("approved_count"))

            # Apply language filter to group sessions (single language field)
            if selected_languages:
                group_qs = group_qs.filter(language__in=selected_languages)

            group = list(group_qs.order_by("-created_at")[:half])

        # Merge
        merged = peer + group
        # Sort based on user preference
        if sort_order == "oldest":
            merged.sort(key=lambda x: x.created_at, reverse=False)
        else:
            merged.sort(key=lambda x: x.created_at, reverse=True)

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

            session_type = (
                "group"
                if hasattr(s, "starts_at") and isinstance(s, GroupSession)
                else "peer"
            )

            # Build item data
            item = {
                "id": str(s.id),
                "title": s.title,
                "description": (
                    s.description[:200] + "..."
                    if s.description and len(s.description) > 200
                    else s.description
                ),
                "starts_at": getattr(s, "starts_at", None),
                "ends_at": getattr(s, "ends_at", None),
                "created_at": s.created_at,
                "host": str(s.host),
                "url": url,
                "type": session_type,
                "filters": s.filters or {},
            }

            # Group session specific fields
            if session_type == "group":
                approved_count = getattr(s, "approved_count", None)
                if approved_count is None:
                    approved_count = s.requests.filter(
                        status=SessionRequestStatusChoices.APPROVED
                    ).count()
                item["remaining_capacity"] = s.capacity - approved_count
                item["capacity"] = s.capacity
                item["language"] = s.language
                item["language_display"] = s.language_display
                item["recurring"] = s.recurring
                item["recurrence_type"] = s.recurrence_type

            # Peer session specific fields
            else:
                item["durations"] = (
                    s.durations_display if hasattr(s, "durations_display") else []
                )
                item["languages"] = (
                    s.languages_display if hasattr(s, "languages_display") else []
                )

            safe_items.append(item)

        # Annotate with user's request status for each session
        user = (
            request.user
            if request and hasattr(request, "user") and request.user.is_authenticated
            else None
        )
        if user:
            # Build lookup of session_id -> latest request status
            peer_ids = [i["id"] for i in safe_items if i["type"] == "peer"]
            group_ids = [i["id"] for i in safe_items if i["type"] == "group"]

            status_map = {
                SessionRequestStatusChoices.APPROVED: "going",
                SessionRequestStatusChoices.PENDING: "pending",
                SessionRequestStatusChoices.REJECTED: "rejected",
            }

            request_statuses = {}
            if peer_ids:
                for req in PeerSessionRequest.objects.filter(
                    attendee=user, session_id__in=peer_ids
                ).order_by("-created_at"):
                    sid = str(req.session_id)
                    if sid not in request_statuses:
                        label = status_map.get(req.status)
                        if label:
                            request_statuses[sid] = label

            if group_ids:
                for req in GroupSessionRequest.objects.filter(
                    attendee=user, session_id__in=group_ids
                ).order_by("-created_at"):
                    sid = str(req.session_id)
                    if sid not in request_statuses:
                        label = status_map.get(req.status)
                        if label:
                            request_statuses[sid] = label

            for item in safe_items:
                rs = request_statuses.get(item["id"])
                if rs:
                    item["request_status"] = rs

        # Apply category filter selections
        if selected_filters:
            filtered_items = []
            for item in safe_items:
                item_filters = item.get("filters", {})
                matches = True
                for group_slug, selected_slugs in selected_filters.items():
                    if not selected_slugs:
                        continue
                    # Check if this item has any of the selected filter values
                    group_data = item_filters.get(group_slug, {})
                    item_slugs = set(group_data.get("items", {}).keys())
                    if not item_slugs.intersection(set(selected_slugs)):
                        matches = False
                        break
                if matches:
                    filtered_items.append(item)
            safe_items = filtered_items

        # Handle pagination
        paginator = None
        page_obj = None
        if enable_pagination:
            paginator = Paginator(safe_items, limit)
            page_obj = paginator.get_page(current_page)
            safe_items = list(page_obj)

        # Store only primitives in context
        ctx["sessions"] = safe_items
        ctx["paginator"] = paginator
        ctx["page_obj"] = page_obj

        # Pass request so pagination template can preserve query params
        if request:
            ctx["request"] = request

        # Pass block settings to template for filter UI
        ctx["show_filters"] = show_filters
        ctx["enable_pagination"] = enable_pagination
        ctx["sort_order"] = sort_order
        ctx["include_peer_sessions"] = include_peer
        ctx["include_group_sessions"] = include_group
        ctx["include_unavailable"] = include_unavailable
        ctx["include_full_capacity"] = include_full_capacity

        # Pass filter categories and language filter data for UI
        ctx["filter_categories"] = filter_categories
        ctx["selected_filters"] = selected_filters
        ctx["available_languages"] = available_languages
        ctx["selected_languages"] = selected_languages
        return ctx
