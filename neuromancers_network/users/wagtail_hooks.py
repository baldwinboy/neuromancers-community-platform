from django.urls import path
from wagtail import hooks

from neuromancers_network.common.views import model_form_fields


@hooks.register("register_admin_urls")
def register_model_form_fields_url():
    return [
        path(
            "api/model-form-fields/users/",
            model_form_fields,
            name="model_form_fields",
        ),
    ]
