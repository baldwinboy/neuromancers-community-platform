from django.forms import modelform_factory
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.viewsets.model import ModelViewSet

from neuromancers_network.core.bulk_actions import ConfirmBulkAction
from neuromancers_network.peers.forms import PeerProfileAdminForm
from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.peers.models import PeerProfile
from neuromancers_network.users.models import UserProfile


class PeerApplicationFilterSet(WagtailFilterSet):
    class Meta:
        model = PeerApplication
        fields = ["status"]


class PeerProfileFilterSet(WagtailFilterSet):
    class Meta:
        model = PeerProfile
        fields = ["is_approved", "is_verified", "countries", "languages"]


class PeerApplicationViewSet(ModelViewSet):
    model = PeerApplication
    icon = "form"
    menu_label = _("Peer applications")
    menu_name = "peer_applications"
    menu_order = 1
    list_display = [
        "user",
        "status",
        "is_approved",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    ]
    search_fields = ["user__username", "user__name", "reason"]
    filterset_class = PeerApplicationFilterSet
    form_fields = [
        "user",
        "reason",
        "is_approved",
        "status",
        "reviewed_by",
        "reviewed_at",
    ]
    list_per_page = 50


class PeerProfileViewSet(ModelViewSet):
    model = PeerProfile
    icon = "user"
    menu_label = _("Peer profiles")
    menu_name = "peer_profiles"
    menu_order = 2
    list_display = ["user", "is_approved", "is_verified", "default_terms_updated_at"]
    search_fields = ["user__username", "user__name", "bio"]
    filterset_class = PeerProfileFilterSet
    form_fields = [
        "bio",
        "default_terms",
        "is_approved",
        "is_verified",
        "languages",
        "countries",
        "tags",
    ]
    list_per_page = 50

    def get_form_class(self, for_update=False):  # noqa: FBT002
        return modelform_factory(
            self.model,
            form=PeerProfileAdminForm,
            fields=self.get_form_fields(),
        )


class UserProfileViewSet(ModelViewSet):
    model = UserProfile
    icon = "user"
    menu_label = _("Member profiles")
    menu_name = "user_profiles"
    menu_order = 3
    list_display = ["user", "visibility", "access_needs_visible_to_peer"]
    search_fields = ["user__username", "user__name"]
    form_fields = ["visibility", "access_needs", "access_needs_visible_to_peer"]
    list_per_page = 50


class ApprovePeerApplicationBulkAction(ConfirmBulkAction):
    models = [PeerApplication]
    display_name = _("Approve application")
    action_type = "approve"
    aria_label = _("Approve selected applications")
    icon = "check"
    confirm_message = _("Approve the selected peer applications?")
    action_button_text = _("Yes, approve")
    no_action_button_text = _("No, go back")

    def get_execution_context(self):
        return {"reviewer": self.request.user}

    @classmethod
    def execute_action(cls, objects, *, reviewer=None, **kwargs):
        for application in objects:
            application.approve(reviewer)
        return len(objects), 0


class RejectPeerApplicationBulkAction(ConfirmBulkAction):
    models = [PeerApplication]
    display_name = _("Reject application")
    action_type = "reject"
    aria_label = _("Reject selected applications")
    icon = "no"
    confirm_message = _("Reject the selected peer applications?")
    action_button_text = _("Yes, reject")
    no_action_button_text = _("No, go back")

    def get_execution_context(self):
        return {"reviewer": self.request.user}

    @classmethod
    def execute_action(cls, objects, *, reviewer=None, **kwargs):
        for application in objects:
            application.reject(reviewer)
        return len(objects), 0


class VerifyPeerBulkAction(ConfirmBulkAction):
    models = [PeerProfile]
    display_name = _("Verify")
    action_type = "verify"
    aria_label = _("Verify selected peers")
    icon = "check"
    confirm_message = _("Mark the selected peers as verified?")
    action_button_text = _("Yes, verify")
    no_action_button_text = _("No, go back")

    def get_execution_context(self):
        return {"reviewer": self.request.user}

    @classmethod
    def execute_action(cls, objects, *, reviewer=None, **kwargs):
        for profile in objects:
            profile.verify(reviewer)
        return len(objects), 0


class UnverifyPeerBulkAction(ConfirmBulkAction):
    models = [PeerProfile]
    display_name = _("Unverify")
    action_type = "unverify"
    aria_label = _("Unverify selected peers")
    icon = "no"
    confirm_message = _("Remove verification from the selected peers?")
    action_button_text = _("Yes, unverify")
    no_action_button_text = _("No, go back")

    def get_execution_context(self):
        return {"reviewer": self.request.user}

    @classmethod
    def execute_action(cls, objects, *, reviewer=None, **kwargs):
        for profile in objects:
            profile.unverify(reviewer)
        return len(objects), 0


for action_class in [
    ApprovePeerApplicationBulkAction,
    RejectPeerApplicationBulkAction,
    VerifyPeerBulkAction,
    UnverifyPeerBulkAction,
]:
    hooks.register("register_bulk_action", action_class)
