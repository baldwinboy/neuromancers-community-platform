"""Admin-authored peer application form pages."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail_daisIE.forms.fields import DaisieFormField

from neuromancers_network.core.forms_pages import ProjectDaisieFormPage


def _reason_for(page, form):
    for clean_name, target in page.get_model_field_map().items():
        if target == "reason":
            return form.cleaned_data.get(clean_name, "")
    return form.cleaned_data.get("reason", "")


class PeerApplicationFormField(DaisieFormField):
    page = ParentalKey(
        "peers.PeerApplicationFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class PeerApplicationFormPage(ProjectDaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    def _reason_value(self, form):
        return _reason_for(self, form)

    def process_form_submission(self, form):
        from wagtail_daisIE.forms.models import FormSubmissionError  # noqa: PLC0415

        from neuromancers_network.peers.models import PeerApplication  # noqa: PLC0415

        user = getattr(getattr(self, "_daisie_request", None), "user", None)
        if user is None or not user.is_authenticated:
            raise FormSubmissionError(_("Sign in to apply."))

        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=user.pk)
            if PeerApplication.objects.filter(user=user).exists():
                raise FormSubmissionError(
                    _("You have already submitted a peer application."),
                )
            return super().process_form_submission(form)

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.peers.models import PeerApplication  # noqa: PLC0415

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        if PeerApplication.objects.filter(user=user).exists():
            return None

        return PeerApplication.objects.create(
            user=user,
            reason=self._reason_value(form),
            submission=submission.form_data if submission is not None else {},
            submission_record=submission,
        )


class PeerApplicationEditFormField(DaisieFormField):
    page = ParentalKey(
        "peers.PeerApplicationEditFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class PeerApplicationEditFormPage(ProjectDaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    form_mode = "edit"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    INSTANCE_MODEL = "peer_application"

    def clean(self):
        self.instance_model = self.INSTANCE_MODEL
        super().clean()

    def get_form(self, *args, **kwargs):
        # ``DaisieFormPage.get_form`` resolves the edit instance before any
        # model validation runs, so the model choice must be set here as well.
        self.instance_model = self.INSTANCE_MODEL
        return super().get_form(*args, **kwargs)

    def _apply_instance_initial(self, form, instance):
        super()._apply_instance_initial(form, instance)
        payload = instance.submission or {}
        if instance.submission_record_id and instance.submission_record:
            payload = instance.submission_record.form_data or payload
        for field in self.get_form_fields():
            name = field.clean_name
            if (
                name in form.fields
                and name in payload
                and not getattr(field, "is_upload", False)
            ):
                form.fields[name].initial = payload[name]

    def process_form_submission(self, form):
        from wagtail_daisIE.forms.models import FormSubmissionError  # noqa: PLC0415

        from neuromancers_network.peers.models import PeerApplication  # noqa: PLC0415
        from neuromancers_network.peers.models import PeerApplicationStatus  # noqa: PLC0415

        user = getattr(getattr(self, "_daisie_request", None), "user", None)
        if user is None or not user.is_authenticated:
            raise FormSubmissionError(_("Sign in to edit your application."))

        with transaction.atomic():
            application = (
                PeerApplication.objects.select_for_update().filter(user=user).first()
            )
            if (
                application is None
                or application.status != PeerApplicationStatus.PENDING
            ):
                raise FormSubmissionError(
                    _("This application can no longer be edited."),
                )
            self._daisie_instance = application
            return super().process_form_submission(form)

    def update_instance_from_submission(self, form, instance, submission=None):
        instance.reason = _reason_for(self, form)
        if submission is not None:
            instance.submission = submission.form_data
            instance.submission_record = submission
        return super().update_instance_from_submission(
            form,
            instance,
            submission=submission,
        )
