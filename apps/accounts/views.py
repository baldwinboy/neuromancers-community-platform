import json
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import DetailView, FormView, TemplateView, View

from apps.accounts.forms import (
    AccountSettingsForm,
    NotificationSettingsForm,
    PeerNotificationSettingsForm,
    PeerPrivacySettingsForm,
    ProfileForm,
)
from apps.accounts.models_users.profile import StripeAccount
from apps.accounts.models_users.user_settings import (
    Notifications,
    NotificationSettings,
    PeerNotificationSettings,
    PeerPrivacySettings,
)
from apps.common.getpronto import GetProntoClient, GetProntoError
from apps.common.utils import (
    get_stripe_oauth,
    get_stripe_oauth_url,
    is_stripe_account_ready,
)
from apps.events.choices import SessionRequestStatusChoices

logger = logging.getLogger(__name__)

User = get_user_model()


def get_calendar_data(user):
    """Generate calendar data for a user's availability and scheduled sessions."""

    from apps.events.models_sessions.group import GroupSession
    from apps.events.models_sessions.peer import PeerSession, PeerSessionRequest

    calendar = {}
    now = timezone.now()
    # Look 3 months ahead
    end_date = now + timedelta(days=90)

    # Get peer session availability
    peer_sessions = PeerSession.objects.filter(host=user, is_published=True)
    for session in peer_sessions:
        if hasattr(session, "available_slots"):
            for start, end in session.available_slots:
                if start >= now and start <= end_date:
                    date_str = start.strftime("%Y-%m-%d")
                    if date_str not in calendar:
                        calendar[date_str] = {
                            "available": False,
                            "scheduled": False,
                            "slots": [],
                            "events": [],
                        }
                    calendar[date_str]["available"] = True
                    calendar[date_str]["slots"].append(
                        {
                            "start": start.strftime("%H:%M"),
                            "end": end.strftime("%H:%M"),
                        }
                    )

    # Get scheduled peer sessions (as host)
    peer_requests = PeerSessionRequest.objects.filter(
        session__host=user,
        status=SessionRequestStatusChoices.APPROVED,
        starts_at__gte=now,
        starts_at__lte=end_date,
    ).select_related("session")

    for req in peer_requests:
        date_str = req.starts_at.strftime("%Y-%m-%d")
        if date_str not in calendar:
            calendar[date_str] = {
                "available": False,
                "scheduled": False,
                "slots": [],
                "events": [],
            }
        calendar[date_str]["scheduled"] = True
        calendar[date_str]["events"].append(
            {
                "type": "peer",
                "title": req.session.title,
                "time": f"{req.starts_at.strftime('%H:%M')} - {req.ends_at.strftime('%H:%M')}",
            }
        )

    # Get group sessions (as host)
    group_sessions = GroupSession.objects.filter(
        host=user,
        is_published=True,
        starts_at__gte=now,
        starts_at__lte=end_date,
    )

    for session in group_sessions:
        date_str = session.starts_at.strftime("%Y-%m-%d")
        if date_str not in calendar:
            calendar[date_str] = {
                "available": False,
                "scheduled": False,
                "slots": [],
                "events": [],
            }
        calendar[date_str]["scheduled"] = True
        calendar[date_str]["events"].append(
            {
                "type": "group",
                "title": session.title,
                "time": f"{session.starts_at.strftime('%H:%M')} - {session.ends_at.strftime('%H:%M')}",
            }
        )

    return json.dumps(calendar)


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    View for logged-in users to see their own profile
    """

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        from apps.events.utils import format_session_for_card

        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Check if user is a peer and has privacy settings
        try:
            privacy = user.peer_privacy_settings
            context["show_calendar"] = privacy.show_calendar
            context["show_peer_session_details"] = privacy.show_peer_session_details
            context["show_group_session_details"] = privacy.show_group_session_details
        except PeerPrivacySettings.DoesNotExist:
            context["show_calendar"] = False
            context["show_peer_session_details"] = False
            context["show_group_session_details"] = False

        if context["show_calendar"]:
            context["calendar_data"] = get_calendar_data(user)

        # Format hosted sessions for session_item component
        hosted_sessions = user.get_hosted_sessions
        context["hosted_sessions"] = [
            format_session_for_card(session, user=user) for session in hosted_sessions
        ]

        # Format sessions user is attending (has active requests for)
        context["attending_sessions"] = self._get_attending_sessions(user)

        return context

    @staticmethod
    def _get_attending_sessions(user):
        """Get sessions the user has requested to attend, formatted for session_item."""
        from apps.events.models_sessions.group import GroupSessionRequest
        from apps.events.models_sessions.peer import PeerSessionRequest
        from apps.events.utils import format_session_for_card

        # Get peer session requests (approved or pending)
        peer_requests = (
            PeerSessionRequest.objects.filter(
                attendee=user,
                status__in=[
                    SessionRequestStatusChoices.APPROVED,
                    SessionRequestStatusChoices.PENDING,
                ],
            )
            .select_related("session", "session__host")
            .order_by("-created_at")
        )

        # Get group session requests (approved or pending)
        group_requests = (
            GroupSessionRequest.objects.filter(
                attendee=user,
                status__in=[
                    SessionRequestStatusChoices.APPROVED,
                    SessionRequestStatusChoices.PENDING,
                ],
            )
            .select_related("session", "session__host")
            .order_by("-created_at")
        )

        # Deduplicate by session (user may have multiple requests for the same session)
        seen_sessions = set()
        attending = []
        for req in list(peer_requests) + list(group_requests):
            session_id = str(req.session.pk)
            if session_id not in seen_sessions:
                seen_sessions.add(session_id)
                attending.append(format_session_for_card(req.session, user=user))

        return attending


class UserView(DetailView):
    """
    View for any user to see other profiles
    """

    model = User
    context_object_name = "other_user"
    template_name = "accounts/user_profile.html"
    pk_url_kwarg = "username"

    def get_object(self):
        return get_object_or_404(
            self.model, username=self.kwargs.get(self.pk_url_kwarg)
        )

    def get_context_data(self, **kwargs):
        from apps.events.utils import format_session_for_card

        context = super().get_context_data(**kwargs)
        user = self.get_object()

        # Check if user is a peer and has privacy settings allowing calendar
        try:
            privacy = user.peer_privacy_settings
            context["show_calendar"] = privacy.show_calendar
            context["show_peer_session_details"] = privacy.show_peer_session_details
            context["show_group_session_details"] = privacy.show_group_session_details
        except PeerPrivacySettings.DoesNotExist:
            context["show_calendar"] = False
            context["show_peer_session_details"] = False
            context["show_group_session_details"] = False

        if context["show_calendar"]:
            context["calendar_data"] = get_calendar_data(user)

        # Format hosted sessions for session_item component
        hosted_sessions = user.get_hosted_sessions
        viewer = self.request.user if self.request.user.is_authenticated else None
        context["hosted_sessions"] = [
            format_session_for_card(session, user=viewer) for session in hosted_sessions
        ]

        return context

    def get(self, request, *args, **kwargs):
        """
        Redirect logged-in users querying their own profile to ProfileView
        """
        username = self.kwargs.get(self.pk_url_kwarg)
        if request.user.is_authenticated and request.user.username == username:
            return redirect("accounts_profile")

        return super().get(self, request, *args, **kwargs)


class UserSettingsView(LoginRequiredMixin, FormView):
    """
    View for logged-in users to manage their settings with tabbed interface
    """

    template_name = "accounts/user_settings.html"
    form_class = ProfileForm  # Default tab

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user.profile
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Determine active tab from query parameter
        active_tab = self.request.GET.get("tab", "account")
        context["active_tab"] = active_tab

        # Account form (name, username, DOB)
        if "account_form" not in context:
            context["account_form"] = AccountSettingsForm(
                instance=self.request.user,
                prefix="account",
            )

        # Profile form (always available)
        if "profile_form" not in context:
            context["profile_form"] = ProfileForm(
                instance=self.request.user.profile,
                user=self.request.user,
                prefix="profile",
            )

        # Notification forms
        if "notification_form" not in context:
            notification_settings, _ = NotificationSettings.objects.get_or_create(
                user=self.request.user
            )
            context["notification_form"] = NotificationSettingsForm(
                instance=notification_settings,
                prefix="notifications",
            )

        # Peer-specific settings (notification and privacy)
        if self.request.user.has_perm("events.add_peersession"):
            if "peer_notification_form" not in context:
                peer_settings, _ = PeerNotificationSettings.objects.get_or_create(
                    user=self.request.user
                )
                context["peer_notification_form"] = PeerNotificationSettingsForm(
                    instance=peer_settings,
                    prefix="peer_notifications",
                )

            if "privacy_form" not in context:
                privacy_settings, _ = PeerPrivacySettings.objects.get_or_create(
                    user=self.request.user
                )
                context["privacy_form"] = PeerPrivacySettingsForm(
                    instance=privacy_settings,
                    prefix="privacy",
                )

        # Stripe account info
        if self.request.user.has_perm("events.add_peersession"):
            try:
                stripe_account = StripeAccount.objects.get(user=self.request.user)
                context["stripe_account"] = stripe_account
            except StripeAccount.DoesNotExist:
                context["stripe_account"] = None

        return context

    def post(self, request, *args, **kwargs):
        """Handle form submissions based on which form was submitted"""
        form_type = request.POST.get("form_type")

        if form_type == "account":
            form = AccountSettingsForm(
                request.POST,
                instance=request.user,
                prefix="account",
            )
            if form.is_valid():
                form.save()
                messages.success(request, "Account details updated successfully")
                return redirect(f"{reverse('accounts_user_settings')}?tab=account")
            else:
                return self.form_invalid_with_context(form, "account_form", "account")

        elif form_type == "profile":
            form = ProfileForm(
                request.POST,
                request.FILES,
                instance=request.user.profile,
                user=request.user,
                prefix="profile",
            )
            if form.is_valid():
                profile = form.save(commit=False)

                # Handle display picture upload to GetPronto
                uploaded_file = form.cleaned_data.get("display_picture_file")
                if uploaded_file:
                    try:
                        client = GetProntoClient(request=request)
                        # Compress the image before uploading
                        buffer, _mime = client.compress_image(
                            uploaded_file,
                            max_dimension=512,
                            quality=85,
                            output_format="WEBP",
                        )
                        filename = f"avatar-{request.user.username}.webp"

                        # Delete old file from GetPronto if one exists
                        if profile.display_picture_id:
                            try:
                                client.delete_file(profile.display_picture_id)
                            except GetProntoError:
                                logger.warning(
                                    "Failed to delete old avatar %s from GetPronto",
                                    profile.display_picture_id,
                                )

                        result = client.upload_file(
                            buffer,
                            filename=filename,
                            custom_filename=filename,
                        )
                        profile.display_picture_url = result.url
                        profile.display_picture_id = result.id
                    except GetProntoError as exc:
                        logger.error("GetPronto upload failed: %s", exc)
                        messages.error(
                            request,
                            "Profile saved but image upload failed. "
                            "Please try uploading your picture again.",
                        )

                profile.has_customized = True
                profile.save()
                messages.success(request, "Profile updated successfully")
                return redirect(f"{reverse('accounts_user_settings')}?tab=profile")
            else:
                return self.form_invalid_with_context(form, "profile_form", "profile")

        elif form_type == "notifications":
            notification_settings, _ = NotificationSettings.objects.get_or_create(
                user=request.user
            )
            form = NotificationSettingsForm(
                request.POST,
                instance=notification_settings,
                prefix="notifications",
            )
            if form.is_valid():
                settings = form.save(commit=False)
                settings.has_customized = True
                settings.save()
                messages.success(request, "Notification settings updated successfully")
                return redirect(
                    f"{reverse('accounts_user_settings')}?tab=notifications"
                )
            else:
                return self.form_invalid_with_context(
                    form, "notification_form", "notifications"
                )

        elif form_type == "peer_notifications":
            if not request.user.has_perm("events.add_peersession"):
                messages.error(
                    request, "You don't have permission to update these settings"
                )
                return redirect(reverse("accounts_user_settings"))

            peer_settings, _ = PeerNotificationSettings.objects.get_or_create(
                user=request.user
            )
            form = PeerNotificationSettingsForm(
                request.POST,
                instance=peer_settings,
                prefix="peer_notifications",
            )
            if form.is_valid():
                settings = form.save(commit=False)
                settings.has_customized = True
                settings.save()
                messages.success(
                    request, "Host notification settings updated successfully"
                )
                return redirect(
                    f"{reverse('accounts_user_settings')}?tab=notifications"
                )
            else:
                return self.form_invalid_with_context(
                    form, "peer_notification_form", "notifications"
                )

        elif form_type == "privacy":
            if not request.user.has_perm("events.add_peersession"):
                messages.error(
                    request, "You don't have permission to update these settings"
                )
                return redirect(reverse("accounts_user_settings"))

            privacy_settings, _ = PeerPrivacySettings.objects.get_or_create(
                user=request.user
            )
            form = PeerPrivacySettingsForm(
                request.POST,
                instance=privacy_settings,
                prefix="privacy",
            )
            if form.is_valid():
                form.save()
                messages.success(request, "Privacy settings updated successfully")
                return redirect(f"{reverse('accounts_user_settings')}?tab=privacy")
            else:
                return self.form_invalid_with_context(form, "privacy_form", "privacy")

        return redirect(reverse("accounts_user_settings"))

    def form_invalid_with_context(self, form, form_key, tab):
        """Helper to render form with errors in correct tab"""
        context = self.get_context_data()
        context[form_key] = form
        context["active_tab"] = tab
        return self.render_to_response(context)


class StripeAuthorizeView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.has_perm("events.add_peersession"):
            return redirect(reverse("accounts_user_settings"))

        return redirect(get_stripe_oauth_url(request))


class StripeAuthorizeCallbackView(LoginRequiredMixin, View):
    def get(self, request):
        next = reverse("accounts_user_settings")

        if not request.user.has_perm("events.add_peersession"):
            return redirect(next)

        code = request.GET.get("code")
        if code:
            try:
                response = get_stripe_oauth(code=code, request=request)
                if response["stripe_user_id"]:
                    account_id = response["stripe_user_id"]

                    is_ready = is_stripe_account_ready(account_id, request=request)

                    stripe_account, created = StripeAccount.objects.get_or_create(
                        user=request.user,
                        defaults={
                            "is_ready": is_ready,
                            "id": response["stripe_user_id"],
                        },
                    )

                    if not created:
                        stripe_account.id = response["stripe_user_id"]
                        stripe_account.is_ready = is_ready
                        stripe_account.save()
            except:  # noqa: E722
                pass

        return redirect(next)


class StripeDisconnectView(LoginRequiredMixin, View):
    """Disconnect user's Stripe account"""

    def post(self, request):
        if not request.user.has_perm("events.add_peersession"):
            messages.error(request, "You don't have permission to disconnect Stripe")
            return redirect(reverse("accounts_user_settings"))

        try:
            StripeAccount.objects.filter(user=request.user).delete()
            messages.success(request, "Stripe account disconnected successfully")
        except Exception as e:
            messages.error(request, f"Error disconnecting Stripe: {str(e)}")

        return redirect(f"{reverse('accounts_user_settings')}?tab=stripe")


class NotificationInboxView(LoginRequiredMixin, TemplateView):
    """
    Display user's notifications in an inbox-style interface.
    """

    template_name = "accounts/notification_inbox.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's notifications, ordered by newest first
        notifications = Notifications.objects.filter(
            sent_to=self.request.user
        ).order_by("-sent_at")

        # Paginate
        paginator = Paginator(notifications, 20)  # 20 per page
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["notifications"] = page_obj.object_list
        context["unread_count"] = notifications.filter(read=False).count()

        return context


class MarkNotificationReadView(LoginRequiredMixin, TemplateView):
    """
    AJAX endpoint to mark a notification as read.
    """

    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notifications, id=notification_id, sent_to=request.user
        )
        notification.read = True
        notification.save(update_fields=["read"])

        return JsonResponse({"success": True})


class MarkAllNotificationsReadView(LoginRequiredMixin, TemplateView):
    """
    AJAX endpoint to mark all notifications as read.
    """

    def post(self, request):
        Notifications.objects.filter(sent_to=request.user, read=False).update(read=True)
        return JsonResponse({"success": True})


class ClearNotificationsView(LoginRequiredMixin, TemplateView):
    """
    Delete all read notifications.
    """

    def post(self, request):
        Notifications.objects.filter(sent_to=request.user, read=True).delete()
        return JsonResponse({"success": True})


class HostDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard for hosts to manage peer/group session requests and refunds.
    """

    template_name = "accounts/host_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_perm("events.add_peersession"):
            messages.error(request, "You don't have permission to access the dashboard")
            return redirect("accounts_profile")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from apps.events.models_sessions.group import GroupSession, GroupSessionRequest
        from apps.events.models_sessions.peer import PeerSession, PeerSessionRequest

        context = super().get_context_data(**kwargs)
        user = self.request.user
        active_tab = self.request.GET.get("tab", "peer")
        context["active_tab"] = active_tab

        # Filter params
        session_filter = self.request.GET.get("session", "")
        time_filter = self.request.GET.get("time", "")
        context["session_filter"] = session_filter
        context["time_filter"] = time_filter

        now = timezone.now()

        # Peer session requests for this host
        peer_qs = (
            PeerSessionRequest.objects.filter(session__host=user)
            .select_related("session", "attendee")
            .order_by("-created_at")
        )
        if session_filter:
            peer_qs = peer_qs.filter(session__pk=session_filter)
        if time_filter == "upcoming":
            peer_qs = peer_qs.filter(starts_at__gte=now)
        elif time_filter == "past":
            peer_qs = peer_qs.filter(starts_at__lt=now)

        context["peer_requests"] = peer_qs
        context["peer_pending_count"] = peer_qs.filter(
            status=SessionRequestStatusChoices.PENDING
        ).count()

        # Group session requests for this host
        group_qs = (
            GroupSessionRequest.objects.filter(session__host=user)
            .select_related("session", "attendee")
            .order_by("-created_at")
        )
        if session_filter:
            group_qs = group_qs.filter(session__pk=session_filter)
        if time_filter == "upcoming":
            group_qs = group_qs.filter(session__starts_at__gte=now)
        elif time_filter == "past":
            group_qs = group_qs.filter(session__starts_at__lt=now)

        context["group_requests"] = group_qs
        context["group_pending_count"] = group_qs.filter(
            status=SessionRequestStatusChoices.PENDING
        ).count()

        # Refund requests (pending refund_status across both types)
        peer_refunds = PeerSessionRequest.objects.filter(
            session__host=user,
            refund_status=SessionRequestStatusChoices.PENDING,
            stripe_payment_intent_id__isnull=False,
        ).select_related("session", "attendee")

        group_refunds = GroupSessionRequest.objects.filter(
            session__host=user,
            refund_status=SessionRequestStatusChoices.PENDING,
            stripe_payment_intent_id__isnull=False,
        ).select_related("session", "attendee")

        refund_requests = list(peer_refunds) + list(group_refunds)
        context["refund_requests"] = refund_requests
        context["refund_pending_count"] = len(refund_requests)

        # Session list for the filter dropdown
        peer_sessions = PeerSession.objects.filter(
            host=user, is_published=True
        ).values_list("pk", "title")
        group_sessions = GroupSession.objects.filter(
            host=user, is_published=True
        ).values_list("pk", "title")
        context["host_sessions"] = list(peer_sessions) + list(group_sessions)

        return context

    def post(self, request, *args, **kwargs):
        """Handle approve/reject actions on requests."""
        from apps.events.models_sessions.group import GroupSessionRequest
        from apps.events.models_sessions.peer import PeerSessionRequest

        request_id = request.POST.get("request_id")
        request_type = request.POST.get("request_type")
        action = request.POST.get("action")

        if not request_id or not request_type or not action:
            messages.error(request, "Invalid request")
            return redirect("host_dashboard")

        ModelCls = PeerSessionRequest if request_type == "peer" else GroupSessionRequest

        try:
            session_request = ModelCls.objects.get(
                pk=request_id, session__host=request.user
            )
        except ModelCls.DoesNotExist:
            messages.error(request, "Request not found")
            return redirect("host_dashboard")

        if action == "approve":
            session_request.status = SessionRequestStatusChoices.APPROVED
            session_request.save(update_fields=["status"])
            messages.success(request, "Request approved")
        elif action == "reject":
            session_request.status = SessionRequestStatusChoices.REJECTED
            session_request.save(update_fields=["status"])
            messages.success(request, "Request rejected")
        elif action == "revoke":
            if session_request.status != SessionRequestStatusChoices.APPROVED:
                messages.error(request, _("Only approved requests can be revoked."))
            else:
                self._revoke_request(session_request, request)

        tab = request.GET.get("tab", request_type)
        return redirect(f"{reverse('host_dashboard')}?tab={tab}")

    def _revoke_request(self, session_request, request):
        """Revoke an approved request — mirrors the attendee withdraw flow.

        Sets the request to WITHDRAWN and handles refund processing
        (automatic or pending-approval). Notifies the attendee.
        """
        import stripe

        from apps.common.utils import get_stripe_secret_key
        from apps.events.notifications import (
            notify_refund_approved,
            notify_request_revoked,
        )

        has_payment = bool(session_request.stripe_payment_intent_id)

        session_request.status = SessionRequestStatusChoices.WITHDRAWN
        session_request.save(update_fields=["status"])

        # Handle refund for paid requests
        if has_payment and not session_request.refunded:
            # Auto-refund — host initiated the revocation so no approval needed
            try:
                stripe.api_key = get_stripe_secret_key(request)
                refund = stripe.Refund.create(
                    payment_intent=session_request.stripe_payment_intent_id,
                    reason="requested_by_customer",
                )
                if refund.status == "succeeded":
                    session_request.refunded = True
                    session_request.refund_status = SessionRequestStatusChoices.APPROVED
                    session_request.save(update_fields=["refunded", "refund_status"])
                    notify_refund_approved(session_request)
                    messages.success(
                        request,
                        _(
                            "Request revoked and payment refunded. "
                            "The attendee has been notified."
                        ),
                    )
                else:
                    messages.warning(
                        request,
                        _(
                            "Request revoked but the refund could not be processed. "
                            "Please handle it manually via Stripe."
                        ),
                    )
            except stripe.error.StripeError:
                messages.warning(
                    request,
                    _(
                        "Request revoked but the refund could not be processed. "
                        "Please handle it manually via Stripe."
                    ),
                )
        else:
            messages.success(
                request,
                _("Request revoked. The attendee has been notified."),
            )

        # Always notify the attendee
        notify_request_revoked(session_request)
