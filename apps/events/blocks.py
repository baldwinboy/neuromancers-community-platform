from wagtail import blocks

from .components.session_feed import SessionFeed


class SessionFeedBlock(blocks.StructBlock):
    include_peer_sessions = blocks.BooleanBlock(required=False, default=True)
    include_group_sessions = blocks.BooleanBlock(required=False, default=True)

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
        template = "events/blocks/session_feed_block.html"

    def render(self, value, context=None):
        """
        Delegates all rendering to a Wagtail Component.
        """
        component = SessionFeed(value)
        return component.render_html(context)
