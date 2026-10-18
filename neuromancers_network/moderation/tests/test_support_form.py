from types import SimpleNamespace

import pytest
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.moderation.models import SupportFormField
from neuromancers_network.moderation.models import SupportFormPage
from neuromancers_network.moderation.models import SupportKind
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _page():
    home = HomePage.objects.first()
    if home is None:
        root = Page.objects.get(depth=1)
        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)
    page = SupportFormPage(title="Contact", slug="contact")
    home.add_child(instance=page)
    return page


def _field(page, *, clean_name, model_field, field_type="singleline"):
    return SupportFormField.objects.create(
        page=page,
        label=clean_name.title(),
        clean_name=clean_name,
        field_type=field_type,
        required=False,
        model_field=model_field,
    )


class TestSupportFormSubmission:
    def test_maps_fields_and_sets_subject_user(self):
        page = _page()
        subject = UserFactory(username="reported")
        _field(page, clean_name="about", model_field="subject_user")
        _field(page, clean_name="message", model_field="message")
        _field(page, clean_name="kind", model_field="kind")
        _field(page, clean_name="internal", model_field="assigned_to")
        reporter = UserFactory()
        page._daisie_request = SimpleNamespace(user=reporter)  # noqa: SLF001
        form = SimpleNamespace(
            cleaned_data={
                "about": subject.username,
                "message": "Spam",
                "kind": "report_user",
                "internal": "ignored",
            },
        )

        ticket = page.create_instance_from_submission(form)

        assert ticket.reporter == reporter
        assert ticket.subject_user == subject
        assert ticket.message == "Spam"
        assert ticket.kind == SupportKind.REPORT_USER
        assert ticket.assigned_to is None

    def test_unknown_subject_is_ignored(self):
        page = _page()
        _field(page, clean_name="about", model_field="subject_user")
        page._daisie_request = SimpleNamespace(user=UserFactory())  # noqa: SLF001
        form = SimpleNamespace(cleaned_data={"about": "nobody-here"})

        ticket = page.create_instance_from_submission(form)

        assert ticket.subject_user is None
