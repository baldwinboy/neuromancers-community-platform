from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks


@hooks.register("register_icons")
def register_icons(icons):
    return icons + [
        "wagtailadmin/icons/stripe.svg",
        "wagtailadmin/icons/whereby.svg",
        "wagtailadmin/icons/filter.svg",
    ]


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("css/common.css"))
