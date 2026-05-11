from wagtail import hooks

from .views import EmailTemplateViewSet


@hooks.register("register_admin_viewset")
def register_email_templates_viewset():
    return EmailTemplateViewSet()
