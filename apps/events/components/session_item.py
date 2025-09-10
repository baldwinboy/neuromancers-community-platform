import calendar
from collections import defaultdict
from datetime import datetime

from django_components import Component, register


@register("session_item")
class SessionItem(Component):
    template_file = "includes/session_item.html"

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "session": self.kwargs["session"],
            "session_type": self.kwargs["session_type"]
        }
