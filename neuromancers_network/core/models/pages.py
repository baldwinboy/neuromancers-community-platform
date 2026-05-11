from neuromancers_network.common.models import StyledFormPageMixin
from neuromancers_network.common.models import StyledPageMixin


class HomePage(StyledPageMixin):
    """The homepage, with hero and content blocks. Inherits optional background
    overrides and content blocks from StyledPageMixin."""

    page_description = (
        "The homepage. Add content blocks and background overrides as needed."
    )

    parent_page_types = [
        "wagtailcore.Page",
    ]  # Prevent adding parent pages above the homepage


class StandardPage(StyledPageMixin):
    """A standard content page with optional background overrides and content blocks.
    Can be used for any regular page on the site."""

    page_description = (
        "A standard content page. Add content blocks and background overrides as needed.",
    )

    parent_page_types = [
        "core.HomePage",
        "core.StandardPage",
    ]  # Allow homepage and other standard pages as parents
    subpage_types = [
        "core.StandardPage",
        "core.StandardFormPage",
    ]  # Allow only other standard pages as children


class BlogIndexPage(StyledPageMixin):
    """A page that lists blog posts. Inherits optional background overrides and
    content blocks from StyledPageMixin."""

    page_description = (
        "A blog index page. Add content blocks and background overrides as needed.",
    )

    parent_page_types = [
        "core.HomePage",
        "core.StandardPage",
    ]
    subpage_types = []


class BlogPage(StyledPageMixin):
    """A page for individual blog posts. Inherits optional background overrides and
    content blocks from StyledPageMixin."""

    page_description = (
        "A blog post page. Add content blocks and background overrides as needed.",
    )

    parent_page_types = [
        "core.BlogIndexPage",
    ]  # Only allow BlogIndexPages as parents
    subpage_types = []  # Prevent adding child pages under blog posts


class StandardFormPage(StyledFormPageMixin):
    """A standard form page with optional background overrides and content blocks.
    Inherits from StyledFormPageMixin to allow per-page design overrides."""

    page_description = (
        "A standard form page. Add content blocks and background overrides as needed.",
    )

    parent_page_types = [
        "core.HomePage",
        "core.StandardPage",
    ]  # Allow homepage and other standard pages as parents
    subpage_types = []  # Prevent adding child pages under form pages


class ContactFormPage(StyledFormPageMixin):
    """A contact form page. Inherits from StyledFormPageMixin to allow per-page
    design overrides and form handling."""

    page_description = (
        "A contact form page. Add content blocks and background overrides as needed.",
    )

    parent_page_types = [
        "core.HomePage",
        "core.StandardPage",
    ]
    subpage_types = []


class ThemeWrapperPage(StyledPageMixin):
    """A page that wraps content in a theme wrapper. Inherits from
    StyledPageMixin to allow per-page design overrides."""

    page_description = (
        "A theme wrapper page. Add content blocks and background overrides as needed.",
    )

    parent_page_types = [
        "core.HomePage",
        "core.StandardPage",
    ]
    subpage_types = [
        "core.StandardPage",
        "core.StandardFormPage",
    ]
