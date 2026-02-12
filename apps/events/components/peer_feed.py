from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.ui.components import Component
from wagtail.contrib.settings.registry import registry

from apps.events.choices import SessionRequestStatusChoices
from apps.events.models_sessions.group import GroupSession
from apps.events.models_sessions.peer import PeerSession, PeerSessionAvailability
from apps.events.utils import parse_csv_string

User = get_user_model()

# Build language code to name mapping
LANGUAGE_MAP = {code: name for code, name in settings.LANGUAGES}
COUNTRY_MAP = {code: name for code, name in settings.COUNTRIES}


def get_filter_settings():
    """Load FilterSettings and return normalized mapping."""
    try:
        filter_settings = registry.get_by_natural_key("events", "FilterSettings").load()
        return filter_settings.get_cached_mapping()
    except Exception:
        return {}


def get_available_languages():
    """Get languages used across all published sessions."""
    peer_languages = set()
    for lang_str in PeerSession.objects.filter(is_published=True).values_list(
        "languages", flat=True
    ):
        if lang_str:
            peer_languages.update(parse_csv_string(lang_str))

    group_languages = set(
        GroupSession.objects.filter(is_published=True).values_list(
            "language", flat=True
        )
    )

    all_codes = peer_languages | group_languages
    return {code: LANGUAGE_MAP.get(code, code) for code in all_codes if code}


def get_available_countries():
    """Get countries from users who host sessions."""
    from apps.accounts.models_users.profile import Profile

    peer_host_ids = PeerSession.objects.filter(is_published=True).values_list(
        "host_id", flat=True
    )
    group_host_ids = GroupSession.objects.filter(is_published=True).values_list(
        "host_id", flat=True
    )
    all_host_ids = set(peer_host_ids) | set(group_host_ids)

    countries = (
        Profile.objects.filter(user_id__in=all_host_ids, country__isnull=False)
        .exclude(country="")
        .values_list("country", flat=True)
        .distinct()
    )
    return {code: COUNTRY_MAP.get(code, code) for code in countries if code}


class PeerFeed(Component):
    template_name = "includes/peer_feed.html"

    def __init__(self, block_value):
        super().__init__()
        self.block_value = block_value

    def get_context_data(self, parent_context=None):
        ctx = super().get_context_data(parent_context).copy()
        limit = self.block_value.get("limit", 10)
        show_filters = self.block_value.get("show_filters", False)
        enable_pagination = self.block_value.get("enable_pagination", False)

        # Get default values from block
        include_unavailable = self.block_value.get("include_unavailable", False)
        include_full_capacity = self.block_value.get("include_full_capacity", False)
        include_peer_sessions = True
        include_group_sessions = True
        sort_order = "newest"

        # Filter selections
        selected_languages = []
        selected_countries = []
        selected_filters = {}  # For FilterSettings categories

        # Load filter options for UI
        filter_categories = get_filter_settings() if show_filters else {}
        available_languages = get_available_languages() if show_filters else {}
        available_countries = get_available_countries() if show_filters else {}

        # Override with request parameters if filters are enabled
        request = parent_context.get("request") if parent_context else None
        current_page = 1
        if show_filters and request:
            if request.GET:
                # Check for filter parameters in request
                if "include_unavailable" in request.GET:
                    include_unavailable = request.GET.get("include_unavailable") == "1"
                if "include_full" in request.GET:
                    include_full_capacity = request.GET.get("include_full") == "1"
                if "include_peer" in request.GET:
                    include_peer_sessions = request.GET.get("include_peer") == "1"
                if "include_group" in request.GET:
                    include_group_sessions = request.GET.get("include_group") == "1"
                if "sort" in request.GET:
                    sort_order = request.GET.get("sort", "newest")

                # Language filter (comma-separated)
                if "languages" in request.GET:
                    lang_param = request.GET.get("languages", "")
                    selected_languages = [
                        v.strip() for v in lang_param.split(",") if v.strip()
                    ]

                # Country filter (comma-separated)
                if "countries" in request.GET:
                    country_param = request.GET.get("countries", "")
                    selected_countries = [
                        v.strip() for v in country_param.split(",") if v.strip()
                    ]

                # Parse category filter selections (FilterSettings)
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

        # Build base query for peer and group sessions based on session type filter
        peer_session_qs = None
        group_session_qs = None

        if include_peer_sessions:
            peer_session_qs = PeerSession.objects.filter(is_published=True)
            # Apply language filter to peer sessions
            if selected_languages:
                lang_q = Q()
                for lang_code in selected_languages:
                    lang_q |= Q(languages__icontains=lang_code)
                peer_session_qs = peer_session_qs.filter(lang_q)

        if include_group_sessions:
            group_session_qs = GroupSession.objects.filter(is_published=True)
            # Apply language filter to group sessions
            if selected_languages:
                group_session_qs = group_session_qs.filter(
                    language__in=selected_languages
                )

        # Get host IDs based on session type filters
        all_host_ids = set()
        if peer_session_qs is not None:
            all_host_ids |= set(
                peer_session_qs.values_list("host_id", flat=True).distinct()
            )
        if group_session_qs is not None:
            all_host_ids |= set(
                group_session_qs.values_list("host_id", flat=True).distinct()
            )

        if not all_host_ids:
            ctx["peers"] = []
            ctx["show_filters"] = show_filters
            ctx["filter_categories"] = filter_categories
            ctx["available_languages"] = available_languages
            ctx["available_countries"] = available_countries
            return ctx

        # Build base queryset
        users = User.objects.filter(pk__in=all_host_ids).select_related("profile")

        # Apply country filter
        if selected_countries:
            users = users.filter(profile__country__in=selected_countries)

        # Filter logic for excluding users based on availability/capacity
        if not include_unavailable:
            # Subquery to check if user has peer sessions with future availability
            available_peer_sessions = PeerSessionAvailability.objects.filter(
                session__host=OuterRef("pk"),
                session__is_published=True,
            ).filter(
                Q(starts_at__gte=now)
                | Q(occurrence__isnull=False, occurrence_ends_at__isnull=True)
                | Q(occurrence__isnull=False, occurrence_ends_at__gte=now)
            )
            has_available_peer = Exists(available_peer_sessions)

            # Subquery for group sessions with capacity (starts_at in future)
            future_group_sessions = GroupSession.objects.filter(
                host=OuterRef("pk"),
                is_published=True,
                starts_at__gte=now,
            )

            if not include_full_capacity:
                # Further filter to check capacity
                future_group_sessions = future_group_sessions.annotate(
                    approved_count=Count(
                        "requests",
                        filter=Q(requests__status=SessionRequestStatusChoices.APPROVED),
                    )
                ).filter(
                    capacity__gt=Subquery(
                        GroupSession.objects.filter(pk=OuterRef("pk"))
                        .annotate(
                            approved=Count(
                                "requests",
                                filter=Q(
                                    requests__status=SessionRequestStatusChoices.APPROVED
                                ),
                            )
                        )
                        .values("approved")[:1]
                    )
                )

            has_available_group = Exists(future_group_sessions)

            # User must have either available peer sessions or available group sessions
            if include_peer_sessions and include_group_sessions:
                users = users.filter(has_available_peer | has_available_group)
            elif include_peer_sessions:
                users = users.filter(has_available_peer)
            elif include_group_sessions:
                users = users.filter(has_available_group)

        # Sort users based on filter preference
        if sort_order == "oldest":
            users = users.order_by("date_joined")
        elif sort_order == "name_asc":
            users = users.order_by("first_name", "last_name", "username")
        elif sort_order == "name_desc":
            users = users.order_by("-first_name", "-last_name", "-username")
        else:
            users = users.order_by("-date_joined")

        # Convert to safe data for template
        safe_peers = []
        for user in users:
            profile = getattr(user, "profile", None)
            certificate = getattr(user, "certificate", None)

            # Get languages from user's peer sessions and convert to display names
            user_peer_sessions = PeerSession.objects.filter(
                host=user, is_published=True
            )
            language_codes = set()
            peer_filters = {}
            for session in user_peer_sessions:
                if session.languages:
                    language_codes.update(parse_csv_string(session.languages))
                # Collect filter tags from sessions
                if session.filters:
                    for group_slug, group_data in session.filters.items():
                        if group_slug not in peer_filters:
                            peer_filters[group_slug] = set()
                        for item_slug in group_data.get("items", {}).keys():
                            peer_filters[group_slug].add(item_slug)

            # Also get languages from group sessions
            user_group_sessions = GroupSession.objects.filter(
                host=user, is_published=True
            )
            for session in user_group_sessions:
                if session.language:
                    language_codes.add(session.language)
                if session.filters:
                    for group_slug, group_data in session.filters.items():
                        if group_slug not in peer_filters:
                            peer_filters[group_slug] = set()
                        for item_slug in group_data.get("items", {}).keys():
                            peer_filters[group_slug].add(item_slug)

            # Convert language codes to display names (e.g., "en" -> "English")
            languages = [
                LANGUAGE_MAP.get(code.strip(), code.strip()) for code in language_codes
            ]

            safe_peers.append(
                {
                    "id": str(user.pk),
                    "username": user.username,
                    "display_name": user.get_full_name() or user.username,
                    "bio": (
                        profile.about[:150] + "..."
                        if profile and profile.about and len(profile.about) > 150
                        else (profile.about if profile else "")
                    ),
                    "country": profile.country if profile else None,
                    "country_display": profile.country_display if profile else None,
                    "has_certificate": certificate is not None,
                    "languages": languages,
                    "language_codes": list(language_codes),
                    "filter_slugs": {k: list(v) for k, v in peer_filters.items()},
                    "display_picture": (
                        profile.display_picture_url
                        if profile and profile.display_picture_url
                        else None
                    ),
                    "profile_url": reverse(
                        "accounts_user_profile", kwargs={"username": user.username}
                    ),
                }
            )

        # Apply FilterSettings category filters (post-query filtering)
        if selected_filters:
            filtered_peers = []
            for peer in safe_peers:
                matches = True
                for group_slug, selected_slugs in selected_filters.items():
                    if not selected_slugs:
                        continue
                    peer_slugs = set(peer.get("filter_slugs", {}).get(group_slug, []))
                    if not peer_slugs.intersection(set(selected_slugs)):
                        matches = False
                        break
                if matches:
                    filtered_peers.append(peer)
            safe_peers = filtered_peers

        # Handle pagination
        paginator = None
        page_obj = None
        if enable_pagination:
            paginator = Paginator(safe_peers, limit)
            page_obj = paginator.get_page(current_page)
            safe_peers = list(page_obj)

        ctx["peers"] = safe_peers
        ctx["paginator"] = paginator
        ctx["page_obj"] = page_obj

        # Pass request so pagination template can preserve query params
        if request:
            ctx["request"] = request

        # Pass block settings to template for filter UI
        ctx["show_filters"] = show_filters
        ctx["enable_pagination"] = enable_pagination
        ctx["sort_order"] = sort_order
        ctx["include_unavailable"] = include_unavailable
        ctx["include_full_capacity"] = include_full_capacity
        ctx["include_peer_sessions"] = include_peer_sessions
        ctx["include_group_sessions"] = include_group_sessions

        # Pass filter options and selections for UI
        ctx["filter_categories"] = filter_categories
        ctx["available_languages"] = available_languages
        ctx["available_countries"] = available_countries
        ctx["selected_languages"] = selected_languages
        ctx["selected_countries"] = selected_countries
        ctx["selected_filters"] = selected_filters
        return ctx
