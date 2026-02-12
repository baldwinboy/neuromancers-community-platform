from django_components import Component, register


@register("peer_item")
class PeerItem(Component):
    template_file = "includes/peer_item.html"

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "peer": self.kwargs["peer"],
        }
