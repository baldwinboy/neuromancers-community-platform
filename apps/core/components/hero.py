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
            "button_text_color": kwargs.get("button_text_color", "black"),
            "button_background_color": kwargs.get(
                "button_background_color", "safeLightAccent"
            ),
            "image": kwargs.get("image", None),
            "top_border_style": kwargs.get("top_border_style", "none"),
            "top_border_color": kwargs.get("top_border_color", ""),
            "top_border_size": kwargs.get("top_border_size", "medium"),
            "bottom_border_style": kwargs.get("bottom_border_style", "none"),
            "bottom_border_color": kwargs.get("bottom_border_color", ""),
            "bottom_border_size": kwargs.get("bottom_border_size", "medium"),
        }
