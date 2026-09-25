"""Draftail font helpers backed by the default Wagtail daisIE theme.

``draftail_text_utils`` reads font families and font URL stylesheets from
module-level list attributes, but ``wagtail_daisIE.utils`` exposes them as
functions that query the database. The PEP 562 module ``__getattr__`` below
bridges the two: ``DRAFTAIL_FONT_FAMILIES`` and ``DRAFTAIL_FONT_URLS`` are
resolved on first access rather than at import time, so importing this module
never touches the database.
"""


def __getattr__(name):
    if name == "DRAFTAIL_FONT_FAMILIES":
        from wagtail_daisIE.utils import get_draftail_font_families  # noqa: PLC0415

        return get_draftail_font_families()
    if name == "DRAFTAIL_FONT_URLS":
        from wagtail_daisIE.utils import get_draftail_font_urls  # noqa: PLC0415

        return get_draftail_font_urls()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
