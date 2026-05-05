from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render

from apps.core.management.commands.build_platform_guide import (
    get_docs_navigation,
    get_docs_page,
)


@staff_member_required
def platform_guide_view(request, page_slug="index"):
    """
    Render the Platform Guide using compiled markdown documentation.

    Documentation is built from markdown files in apps/core/docs/
    using the build_platform_guide management command.

    Staff members only.
    """
    # Get the requested page
    page_data = get_docs_page(page_slug)

    if not page_data:
        raise Http404(f"Documentation page not found: {page_slug}")

    # Get navigation for sidebar
    navigation = get_docs_navigation()

    return render(
        request,
        "wagtailadmin/platform_guide.html",
        {
            "content": page_data["html"],
            "title": page_data["title"],
            "toc": page_data.get("toc", ""),
            "navigation": navigation,
            "current_page": page_slug,
        },
    )
