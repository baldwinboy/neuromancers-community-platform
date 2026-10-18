from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import FieldRowPanel
from wagtail.admin.panels import MultiFieldPanel
from wagtail.admin.panels import ObjectList
from wagtail.snippets.views.snippets import SnippetViewSet

from neuromancers_network.core.bulk_actions import ConfirmBulkAction
from neuromancers_network.core.views.viewset import HiddenFromSnippetIndexMixin
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


class UserProfileFilterSet(WagtailFilterSet):
    class Meta:
        model = UserProfile
        fields = ["user__accepted_tos", "visibility"]


class PeerApplicationViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
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
    panels = [
        FieldPanel("user"),
        FieldPanel("reason"),
        FieldPanel("is_approved"),
        FieldPanel("status"),
        FieldPanel("reviewed_by"),
        FieldPanel("reviewed_at"),
    ]
    list_per_page = 50


class PeerProfileViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
    model = PeerProfile
    icon = "group"
    menu_label = _("Peer profiles")
    menu_name = "peer_profiles"
    menu_order = 2
    list_display = ["user", "is_approved", "is_verified", "default_terms_updated_at"]
    search_fields = ["user__username", "user__name", "bio"]
    filterset_class = PeerProfileFilterSet
    list_per_page = 50
    edit_handler = ObjectList(
        [
            FieldPanel("user"),
            FieldPanel("bio"),
            FieldPanel("default_terms"),
            MultiFieldPanel(
                [
                    FieldPanel("is_approved"),
                    FieldPanel("is_verified"),
                ],
                heading=_("Approval"),
                classname="collapsed",
            ),
            MultiFieldPanel(
                [
                    FieldRowPanel(
                        [
                            FieldPanel(
                                "languages",
                                classname="w-combobox__menu col6",
                                widget=forms.CheckboxSelectMultiple,
                            ),
                            FieldPanel(
                                "countries",
                                classname="w-combobox__menu col6",
                                widget=forms.CheckboxSelectMultiple,
                            ),
                        ],
                    ),
                    FieldPanel("tags"),
                ],
                heading=_("Filters"),
                classname="collapsed",
            ),
        ],
        base_form_class=PeerProfileAdminForm,
    )


class UserProfileViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
    model = UserProfile
    icon = "user"
    menu_label = _("Member profiles")
    menu_name = "user_profiles"
    menu_order = 3
    list_display = ["user", "visibility", "access_needs_visible_to_peer"]
    search_fields = ["user__username", "user__name"]
    filterset_class = UserProfileFilterSet
    panels = [
        FieldPanel("user"),
        FieldPanel("visibility"),
        FieldPanel("bio"),
        FieldPanel("access_needs"),
        FieldPanel("access_needs_visible_to_peer"),
    ]
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


class ResetTosBulkAction(ConfirmBulkAction):
    models = [UserProfile]
    display_name = _("Reset Terms acceptance")
    action_type = "reset_tos"
    aria_label = _("Reset Terms acceptance for selected members")
    icon = "warning"
    confirm_message = _("Require the selected members to accept the Terms again?")
    action_button_text = _("Yes, reset")
    no_action_button_text = _("No, go back")

    def get_all_objects_in_listing_query(self, parent_id):
        """Honour the listing filters so select-all reproduces the filter."""
        queryset = UserProfile.objects.all()
        filterset_class = UserProfileViewSet.filterset_class
        if filterset_class is not None:
            filterset = filterset_class(data=self.request.GET, queryset=queryset)
            if filterset.is_valid():
                queryset = filterset.qs
        return queryset.values_list("pk", flat=True)

    @classmethod
    def execute_action(cls, objects, **kwargs):
        user_ids = [profile.user_id for profile in objects]
        updated = (
            get_user_model()
            .objects.filter(
                pk__in=user_ids,
                accepted_tos=True,
            )
            .update(accepted_tos=False)
        )
        return updated, 0


for action_class in [
    ApprovePeerApplicationBulkAction,
    RejectPeerApplicationBulkAction,
    VerifyPeerBulkAction,
    UnverifyPeerBulkAction,
    ResetTosBulkAction,
]:
    hooks.register("register_bulk_action", action_class)
