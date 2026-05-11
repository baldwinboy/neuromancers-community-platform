from django.urls import path
from wagtail import hooks

from .views import model_form_fields


@hooks.register("register_icons")
def register_icons(icons):
    return [*icons, "common/icons/palette.svg"]


@hooks.register("register_admin_urls")
def register_model_form_fields_url():
    return [
        path(
            "api/model-form-fields/<str:app_label>/<str:model>/",
            model_form_fields,
            name="model_form_fields",
        ),
    ]
