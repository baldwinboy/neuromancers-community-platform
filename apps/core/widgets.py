from django import forms


class TypedSelectMultiple(forms.SelectMultiple):
    """
    The input type will always be "text" for accessibility purposes. Use "pattern" on initialisation and enter a JS compatible regular expression to add input constraints.
    """

    template_name = "forms/widgets/typed_select_multiple.html"

    class Media:
        js = ["js/typed_multiple_select.js"]

    def __init__(self, attrs=None, choices=(), pattern=None):
        super().__init__(attrs)
        self.choices = choices
        self.pattern = pattern

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        if context.get("widget") and context["widget"].get("attrs"):
            for k, _ in list(context["widget"]["attrs"].items()):
                if k == "required":
                    del context["widget"]["attrs"][k]

        context["widget"]["pattern"] = self.pattern

        return context
