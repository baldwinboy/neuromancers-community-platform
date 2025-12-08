from wagtail import hooks


@hooks.register("register_icons")
def register_icons(icons):
    return icons + ["wagtailadmin/icons/stripe.svg", "wagtailadmin/icons/whereby.svg"]
