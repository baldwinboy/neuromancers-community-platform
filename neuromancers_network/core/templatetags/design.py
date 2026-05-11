from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def build_decl(block) -> str:
    block_type = block.block_type
    val = block.value
    if block_type == "flat":
        return f"background-color: {val['color']};"
    if block_type == "gradient":
        return f"background-image: linear-gradient({val['direction']}, {val['start_color']}, {val['end_color']});"
    if block_type == "image":
        opacity = val.get("opacity", 1)
        return f"background-image: url({val['image'].file.url}); opacity: {opacity};"
    if block_type == "gradient_image":
        grad = val["gradient"]
        img = val["image"]
        opacity = val.get("opacity", 1)
        return (
            f"background-image: linear-gradient({grad['direction']}, {grad['start_color']}, {grad['end_color']}), "
            f"url({img.file.url}); opacity: {opacity};"
        )
    return ""


@register.simple_tag(takes_context=True)
def render_background_css(context):
    page = context.get("page")
    backgrounds = None
    if page and hasattr(page, "page_background") and page.page_background:
        backgrounds = page.page_background
    else:
        site_design = context.get("site_design")
        if site_design and site_design.get("backgrounds"):
            backgrounds = site_design["backgrounds"]

    if not backgrounds:
        return ""

    css_rules = []
    for block in backgrounds:
        mode = block.value.get("mode", "system")
        decl = build_decl(block)
        if mode == "system":
            css_rules.append(f":root {{ {decl} }}")
        elif mode == "light":
            css_rules.append(f":root, [data-theme='light'] {{ {decl} }}")
        elif mode == "dark":
            css_rules.append(
                f"@media (prefers-color-scheme: dark) {{ :root {{ {decl} }} }}",
            )
            css_rules.append(f"[data-theme='dark'] {{ {decl} }}")
    return mark_safe("\n".join(css_rules))
