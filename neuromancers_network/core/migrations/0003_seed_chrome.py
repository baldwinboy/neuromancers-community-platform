"""Seed the default theme, chrome menus, error pages and base page tree."""

from django.db import migrations

ERROR_PAGES = {
    400: "Bad request",
    401: "Not authorised",
    403: "Forbidden",
    404: "Page not found",
    429: "Too many requests",
    500: "Something went wrong",
}


def _seed_theme(apps):
    DaisyUITheme = apps.get_model("wagtail_daisIE", "DaisyUITheme")
    theme, _ = DaisyUITheme.objects.get_or_create(
        name="neuromancers",
        defaults={"default": True},
    )
    for relation in ("colors", "radii", "sizes", "effects", "background"):
        manager = getattr(theme, relation)
        if not manager.exists():
            manager.create()
    return theme


def _seed_menus(apps):
    DaisyUIMenu = apps.get_model("wagtail_daisIE_menus", "DaisyUIMenu")
    for name, layout in (
        ("Main navigation", "navbar"),
        ("Footer", "footer"),
    ):
        DaisyUIMenu.objects.get_or_create(name=name, defaults={"layout": layout})


def _seed_error_pages(apps):
    ErrorPage = apps.get_model("wagtail_daisIE_errors", "ErrorPage")
    for status_code, title in ERROR_PAGES.items():
        ErrorPage.objects.get_or_create(
            status_code=status_code,
            defaults={"title": title, "is_active": True},
        )


def _ensure_child(parent, page_class, *, slug, title):
    existing = parent.get_children().filter(slug=slug).first()
    if existing is not None:
        return existing.specific
    page = page_class(title=title, slug=slug, live=True)
    parent.add_child(instance=page)
    page.save_revision().publish()
    return page


def _seed_pages(apps):
    Page = apps.get_model("wagtailcore", "Page")
    Site = apps.get_model("wagtailcore", "Site")
    HomePage = apps.get_model("core", "HomePage")
    SearchPage = apps.get_model("core", "SearchPage")
    ProfileIndexPage = apps.get_model("core", "ProfileIndexPage")
    DashboardPage = apps.get_model("core", "DashboardPage")
    SettingsPage = apps.get_model("core", "SettingsPage")

    root = Page.objects.filter(depth=1).first()
    if root is None:
        return

    home = HomePage.objects.first()
    if home is None:
        welcome = Page.objects.filter(depth=2, slug="home").first()
        if welcome is not None:
            welcome.slug = "welcome-page"
            welcome.live = False
            welcome.save(update_fields=["slug", "live"])
        home = HomePage(title="NEUROMANCERS Network", slug="home", live=True)
        root.add_child(instance=home)
        home.save_revision().publish()

    _ensure_child(home, SearchPage, slug="search", title="Search")
    _ensure_child(home, ProfileIndexPage, slug="u", title="Members")
    _ensure_child(home, DashboardPage, slug="dashboard", title="Dashboard")
    _ensure_child(home, SettingsPage, slug="settings", title="Settings")

    site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()
    if site is not None and site.root_page_id != home.pk:
        site.root_page = home
        site.save(update_fields=["root_page"])


def forwards(apps, schema_editor):
    _seed_theme(apps)
    _seed_menus(apps)
    _seed_error_pages(apps)
    _seed_pages(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_initial"),
        ("wagtail_daisIE", "0001_initial"),
        ("wagtail_daisIE_menus", "0001_initial"),
        ("wagtail_daisIE_errors", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
