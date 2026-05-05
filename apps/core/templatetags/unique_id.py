import uuid

from django.template.defaulttags import register


@register.simple_tag
def unique_id():
    return str(uuid.uuid4())
