from wagtail.admin.forms.models import WagtailAdminModelForm

from neuromancers_network.taxonomy.forms import AllowedTagsCountriesFormMixin


class MeetingAdminForm(AllowedTagsCountriesFormMixin, WagtailAdminModelForm):
    """Admin form enforcing that meeting tags/countries are allowed."""
