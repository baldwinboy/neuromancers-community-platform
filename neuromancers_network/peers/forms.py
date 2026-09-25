from wagtail.admin.forms.models import WagtailAdminModelForm

from neuromancers_network.taxonomy.forms import AllowedTagsCountriesFormMixin


class PeerProfileAdminForm(AllowedTagsCountriesFormMixin, WagtailAdminModelForm):
    """Admin form enforcing that peer tags/countries are allowed."""
