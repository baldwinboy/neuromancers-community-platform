from django_components import Component, register


@register("hero")
class Hero(Component):
    template_file = "includes/hero.html"
    js_file = "js/hero.js"

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "min_height": kwargs.get("min_height", "400px"),
            "background_color": kwargs.get("background_color", "black"),
            "text_color": kwargs.get("text_color", "white"),
            "heading": kwargs.get("heading", ""),
            "subheading": kwargs.get("subheading", ""),
            "button_text": kwargs.get("button_text", ""),
            "button_link": kwargs.get("button_link", "#"),
            "image": kwargs.get("image", None),
        }
