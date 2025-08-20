from django_components import Component, register


@register("accordion")
class Accordion(Component):
    template_file = "includes/accordion.html"
