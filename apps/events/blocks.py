import logging

from django.utils.functional import cached_property
from wagtail import blocks
from wagtail.contrib.settings.registry import registry

from .components.peer_feed import PeerFeed
from .components.session_feed import SessionFeed

logger = logging.getLogger(__name__)


class SessionFeedBlock(blocks.StructBlock):
    include_peer_sessions = blocks.BooleanBlock(required=False, default=True)
    include_group_sessions = blocks.BooleanBlock(required=False, default=True)
    include_unavailable = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Include peer sessions without availability",
    )
    include_full_capacity = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Include group sessions at full capacity",
    )

    show_filters = blocks.BooleanBlock(required=False, default=False)
    enable_pagination = blocks.BooleanBlock(required=False, default=False)

    limit = blocks.IntegerBlock(
        default=10,
        min_value=1,
        max_value=50,
        help_text="Maximum number of sessions to display (per page if paginated)",
    )

    class Meta:
        icon = "list-ul"
        label = "Session Feed"

    def render(self, value, context=None):
        """
        Delegates all rendering to a Wagtail Component.
        Passes the full context including request for filter handling.
        """
        component = SessionFeed(value)
        # Pass context as parent_context to preserve request object
        return component.render_html(parent_context=context)


class PeerFeedBlock(blocks.StructBlock):
    include_unavailable = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Include peers with only unavailable sessions",
    )
    include_full_capacity = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Include peers with only full-capacity group sessions",
    )

    show_filters = blocks.BooleanBlock(required=False, default=False)
    enable_pagination = blocks.BooleanBlock(required=False, default=False)

    limit = blocks.IntegerBlock(
        default=10,
        min_value=1,
        max_value=50,
        help_text="Maximum number of peers to display (per page if paginated)",
    )

    class Meta:
        icon = "group"
        label = "Peer Feed"

    def render(self, value, context=None):
        """
        Delegates all rendering to a Wagtail Component.
        Passes the full context including request for filter handling.
        """
        component = PeerFeed(value)
        # Pass context as parent_context to preserve request object
        return component.render_html(parent_context=context)


class FilterSelectionBlock(blocks.StructBlock):
    group = blocks.ChoiceBlock(required=True)
    items = blocks.MultipleChoiceBlock(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate group choices dynamically
        self.child_blocks["group"].choices = self.group_choices

    @cached_property
    def normalized_filters(self):
        try:
            filter_settings = registry.get_by_natural_key(
                "events", "FilterSettings"
            ).load()
            return filter_settings.get_cached_mapping()
        except Exception:
            # Table may not exist yet during migrations or DB reset
            logger.debug(
                "FilterSettings table not available yet, returning empty filters."
            )
            return {}

    @property
    def group_choices(self):
        return [(slug, data["label"]) for slug, data in self.normalized_filters.items()]

    def get_form_state(self, value):
        """
        Dynamically populate item choices depending on selected group.
        """
        form_state = super().get_form_state(value)

        if value and value.get("group"):
            group_slug = value["group"]
            group = self.normalized_filters.get(group_slug)

            if group:
                self.child_blocks["items"].choices = [
                    (slug, item["label"]) for slug, item in group["items"].items()
                ]

        return form_state

    class Meta:
        icon = "tag"
        label = "Filters"
        collapsed = True
