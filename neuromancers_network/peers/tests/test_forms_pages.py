from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from wagtail.contrib.forms.models import FormSubmission

from neuromancers_network.core.forms_pages import FormFieldWrapperBlock
from neuromancers_network.core.models import HomePage
from neuromancers_network.peers.forms_pages import PeerApplicationFormField
from neuromancers_network.peers.forms_pages import PeerApplicationFormPage
from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.peers.submissions import answer_rows
from neuromancers_network.peers.submissions import summary
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _page() -> PeerApplicationFormPage:
    home = HomePage.objects.first()
    assert home is not None
    page = PeerApplicationFormPage(title="Apply", slug="apply")
    home.add_child(instance=page)
    return page


def _field(
    page: PeerApplicationFormPage,
    label: str,
    *,
    field_type: str = "multiline",
    model_field: str = "",
    required: bool = True,
) -> PeerApplicationFormField:
    return PeerApplicationFormField.objects.create(
        page=page,
        label=label,
        field_type=field_type,
        model_field=model_field,
        required=required,
    )


def _wrapper(field_name: str) -> tuple[str, dict]:
    return (
        "form_field_wrapper",
        {
            "field": field_name,
            "design": {"padding": {"all_padding": "p-4"}},
            "audience": {"audience": []},
        },
    )


def test_reason_maps_from_model_field():
    page = _page()
    field = _field(page, "Why do you want to join?", model_field="reason")

    form = SimpleNamespace(cleaned_data={field.clean_name: "Because"})

    assert page._reason_value(form) == "Because"  # noqa: SLF001


def test_reason_falls_back_to_clean_name():
    page = _page()
    field = _field(page, "Reason")

    form = SimpleNamespace(cleaned_data={field.clean_name: "Because"})

    assert page._reason_value(form) == "Because"  # noqa: SLF001


def test_placed_fields_include_wrapped_fields():
    page = _page()
    page.body = [_wrapper("reason")]

    assert page.get_placed_field_names() == ["reason"]


def test_duplicate_wrapped_fields_are_rejected():
    page = _page()
    page.body = [_wrapper("reason"), _wrapper("reason")]

    with pytest.raises(ValidationError):
        page.clean()


def test_wrapper_copies_the_bound_form_context():
    form = object()
    value = _wrapper("reason")[1]

    context = FormFieldWrapperBlock().get_context(
        value,
        {"form": form, "request": None},
    )

    assert context["form"] is form
    assert "p-4" in context["block_css"]


def test_create_application_links_the_submission_and_reason():
    page = _page()
    field = _field(page, "Why do you want to join?", model_field="reason")
    user = UserFactory()
    page._daisie_request = SimpleNamespace(user=user)  # noqa: SLF001
    submission = FormSubmission.objects.create(
        page=page,
        form_data={field.clean_name: "Because"},
    )

    application = page.create_instance_from_submission(
        SimpleNamespace(cleaned_data={field.clean_name: "Because"}),
        submission,
    )

    assert application is not None
    assert application.reason == "Because"
    assert application.submission_record == submission


def test_answer_rows_use_current_field_labels_and_values():
    page = _page()
    _field(page, "Reason", model_field="reason")
    _field(page, "Experience", required=False)
    _field(page, "Confirm", field_type="checkbox")
    submission = FormSubmission.objects.create(
        page=page,
        form_data={
            "reason": "Because",
            "experience": "5 years",
            "confirm": True,
        },
    )
    application = PeerApplication.objects.create(
        user=UserFactory(),
        reason="Because",
        submission=submission.form_data,
        submission_record=submission,
    )

    assert {(row["label"], row["value"]) for row in answer_rows(application)} == {
        ("Reason", "Because"),
        ("Experience", "5 years"),
        ("Confirm", "Yes"),
    }


def test_answer_rows_fall_back_to_humanized_json():
    application = PeerApplication.objects.create(
        user=UserFactory(),
        reason="Because",
        submission={"custom_answer": "Value"},
    )

    assert answer_rows(application) == [
        {"label": "Custom Answer", "value": "Value"},
    ]


def test_summary_is_a_short_answer_preview():
    application = PeerApplication.objects.create(
        user=UserFactory(),
        reason="Because",
        submission={"reason": "Because", "experience": "5 years"},
    )

    assert summary(application) == "Reason: Because · Experience: 5 years"
