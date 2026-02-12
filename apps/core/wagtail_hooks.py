from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks


@hooks.register("register_icons")
def register_icons(icons):
    return icons + [
        "wagtailadmin/icons/stripe.svg",
        "wagtailadmin/icons/whereby.svg",
        "wagtailadmin/icons/filter.svg",
        "wagtailadmin/icons/emoji.svg",
    ]


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html(
        '<link rel="stylesheet" href="{}">' '<link rel="stylesheet" href="{}">',
        static("css/common.css"),
        static("css/emoji_picker.css"),
    )


@hooks.register("insert_global_admin_js")
def global_admin_js():
    return format_html('<script src="{}"></script>', static("js/emoji_picker.js"))
