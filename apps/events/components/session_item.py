from django_components import Component, register


@register("session_item")
class SessionItem(Component):
    template_file = "includes/session_item.html"

    def get_template_data(self, args, kwargs, slots, context):
        session = self.kwargs.get("session", {})
        session_type = self.kwargs.get("session_type", session.get("type", "peer"))

        return {
            "session": session,
            "session_type": session_type,
        }
