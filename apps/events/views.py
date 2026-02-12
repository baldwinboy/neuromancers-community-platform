"""
Stripe payment and refund views for session requests.
"""

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.common.utils import get_stripe_secret_key
from apps.events.choices import SessionRequestStatusChoices
from apps.events.models import GroupSessionRequest, PeerSessionRequest
from apps.events.notifications import (
    notify_payment_made,
    notify_payment_received,
    notify_refund_approved,
    notify_refund_requested,
)


def _get_session_request(request_id, **filters):
    """Look up a session request by PK across both PeerSessionRequest and
    GroupSessionRequest.  Returns the instance or None."""
    try:
        return PeerSessionRequest.objects.get(pk=request_id, **filters)
    except PeerSessionRequest.DoesNotExist:
        pass
    try:
        return GroupSessionRequest.objects.get(pk=request_id, **filters)
    except GroupSessionRequest.DoesNotExist:
        return None


class WithdrawPeerRequestView(LoginRequiredMixin, View):
    """Allow a user to withdraw their pending or approved peer session request.

    For approved requests with payments:
    - If the session does NOT require refund approval, the Stripe refund is
      processed automatically and the request is withdrawn.
    - If the session DOES require refund approval, the refund status is set to
      PENDING and the host is notified. The request is still withdrawn.
    """

    def post(self, request, request_id):
        try:
            session_request = PeerSessionRequest.objects.get(
                pk=request_id,
                attendee=request.user,
            )
        except PeerSessionRequest.DoesNotExist:
            messages.error(request, _("This request could not be found."))
            return redirect("accounts_profile")

        session_url = (
            session_request.session.page.full_url
            if hasattr(session_request.session, "page")
            else "/"
        )

        # Gracefully handle already-withdrawn or non-actionable requests
        if session_request.status not in (
            SessionRequestStatusChoices.PENDING,
            SessionRequestStatusChoices.APPROVED,
        ):
            messages.info(request, _("This request has already been withdrawn."))
            return redirect(session_url)

        was_approved = session_request.status == SessionRequestStatusChoices.APPROVED
        has_payment = bool(session_request.stripe_payment_intent_id)

        # Withdraw the request
        session_request.status = SessionRequestStatusChoices.WITHDRAWN
        session_request.save(update_fields=["status"])

        # Handle refund for approved requests with payments
        if was_approved and has_payment and not session_request.refunded:
            if session_request.session.require_refund_approval:
                # Host must approve the refund
                session_request.refund_status = SessionRequestStatusChoices.PENDING
                session_request.save(update_fields=["refund_status"])
                notify_refund_requested(session_request)
                messages.success(
                    request,
                    _(
                        "Your request has been withdrawn. "
                        "A refund request has been submitted and is pending host approval."
                    ),
                )
            else:
                # Automatic refund
                success = self._process_refund(session_request, request)
                if success:
                    notify_refund_approved(session_request)
                    messages.success(
                        request,
                        _(
                            "Your request has been withdrawn and your payment has been refunded."
                        ),
                    )
                else:
                    messages.warning(
                        request,
                        _(
                            "Your request has been withdrawn but the refund could not be processed. "
                            "Please contact support."
                        ),
                    )
        else:
            messages.success(request, _("Your request has been withdrawn."))

        return redirect(session_url)

    def _process_refund(self, session_request, request):
        """Process the actual refund via Stripe."""
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
                return True

            return False

        except stripe.error.StripeError:
            return False


class WithdrawGroupRequestView(LoginRequiredMixin, View):
    """Allow a user to withdraw their pending or approved group session request.

    For approved requests with payments:
    - If the session does NOT require refund approval, the Stripe refund is
      processed automatically and the request is withdrawn.
    - If the session DOES require refund approval, the refund status is set to
      PENDING and the host is notified. The request is still withdrawn.
    """

    def post(self, request, request_id):
        try:
            session_request = GroupSessionRequest.objects.get(
                pk=request_id,
                attendee=request.user,
            )
        except GroupSessionRequest.DoesNotExist:
            messages.error(request, _("This request could not be found."))
            return redirect("accounts_profile")

        session_url = (
            session_request.session.page.full_url
            if hasattr(session_request.session, "page")
            else "/"
        )

        # Gracefully handle already-withdrawn or non-actionable requests
        if session_request.status not in (
            SessionRequestStatusChoices.PENDING,
            SessionRequestStatusChoices.APPROVED,
        ):
            messages.info(request, _("This request has already been withdrawn."))
            return redirect(session_url)

        was_approved = session_request.status == SessionRequestStatusChoices.APPROVED
        has_payment = bool(session_request.stripe_payment_intent_id)

        # Withdraw the request
        session_request.status = SessionRequestStatusChoices.WITHDRAWN
        session_request.save(update_fields=["status"])

        # Handle refund for approved requests with payments
        if was_approved and has_payment and not session_request.refunded:
            if session_request.session.require_refund_approval:
                # Host must approve the refund
                session_request.refund_status = SessionRequestStatusChoices.PENDING
                session_request.save(update_fields=["refund_status"])
                notify_refund_requested(session_request)
                messages.success(
                    request,
                    _(
                        "Your request has been withdrawn. "
                        "A refund request has been submitted and is pending host approval."
                    ),
                )
            else:
                # Automatic refund
                success = self._process_refund(session_request, request)
                if success:
                    notify_refund_approved(session_request)
                    messages.success(
                        request,
                        _(
                            "Your request has been withdrawn and your payment has been refunded."
                        ),
                    )
                else:
                    messages.warning(
                        request,
                        _(
                            "Your request has been withdrawn but the refund could not be processed. "
                            "Please contact support."
                        ),
                    )
        else:
            messages.success(request, _("Your request has been withdrawn."))

        return redirect(session_url)

    def _process_refund(self, session_request, request):
        """Process the actual refund via Stripe."""
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
                return True

            return False

        except stripe.error.StripeError:
            return False


class CreatePaymentLinkView(LoginRequiredMixin, View):
    """Create a Stripe Payment Link for a session request and redirect the user.

    Price priority:
    1. Per-hour price (peer sessions only) – calculated from request duration
    2. Standard flat price on the session
    Concessionary pricing is used when the attendee requested it *and* the
    request was approved with concessionary status.
    """

    def _calculate_amount(self, session_request):
        """Return the amount in the smallest currency unit (e.g. pence/cents)."""
        session = session_request.session
        is_peer = isinstance(session_request, PeerSessionRequest)
        use_concessionary = (
            session_request.pay_concessionary_price
            and session_request.concessionary_status
            == SessionRequestStatusChoices.APPROVED
        )

        if use_concessionary:
            if is_peer and session.concessionary_per_hour_price:
                duration_hrs = (
                    session_request.ends_at - session_request.starts_at
                ).total_seconds() / 3600
                return int(duration_hrs * session.concessionary_per_hour_price)
            return session.concessionary_price or 0

        if is_peer and session.per_hour_price:
            duration_hrs = (
                session_request.ends_at - session_request.starts_at
            ).total_seconds() / 3600
            return int(duration_hrs * session.per_hour_price)

        return session.price or 0

    def get(self, request, request_id):
        session_request = _get_session_request(request_id, attendee=request.user)
        if session_request is None:
            messages.error(request, _("Session request not found."))
            return redirect("accounts_profile")

        # Already paid
        if session_request.stripe_payment_intent_id:
            messages.info(request, _("This session has already been paid for."))
            return redirect("payment_history")

        # Must be approved
        if session_request.status != SessionRequestStatusChoices.APPROVED:
            messages.error(
                request,
                _("This session request must be approved before payment."),
            )
            return redirect("accounts_profile")

        amount = self._calculate_amount(session_request)
        if amount <= 0:
            messages.info(request, _("This is a free session — no payment required."))
            return redirect("accounts_profile")

        # Host must have a connected Stripe account
        if not hasattr(session_request.session.host, "stripe_account"):
            messages.error(
                request,
                _(
                    "The host has not connected a payment account yet. "
                    "Payment is not available at this time."
                ),
            )
            return redirect("accounts_profile")

        try:
            stripe.api_key = get_stripe_secret_key(request)

            application_fee = int(amount * settings.STRIPE_APPLICATION_FEE)
            success_url = request.build_absolute_uri("/payments/success/")
            success_url += "?session_id={CHECKOUT_SESSION_ID}"

            payment_link = stripe.PaymentLink.create(
                line_items=[
                    {
                        "price_data": {
                            "currency": session_request.session.currency.lower(),
                            "product_data": {
                                "name": session_request.session.title,
                                "description": (
                                    f"Session hosted by "
                                    f"{session_request.session.host.username}"
                                ),
                            },
                            "unit_amount": amount,
                        },
                        "quantity": 1,
                    }
                ],
                application_fee_amount=application_fee,
                transfer_data={
                    "destination": session_request.session.host.stripe_account.id,
                },
                after_completion={
                    "type": "redirect",
                    "redirect": {"url": success_url},
                },
                metadata={
                    "session_request_id": str(session_request.id),
                    "session_title": session_request.session.title,
                    "attendee_id": str(request.user.id),
                },
                submit_type="book",
            )

            # Persist the payment link id so we can reconcile later
            session_request.stripe_payment_intent_id = payment_link.id
            session_request.save(update_fields=["stripe_payment_intent_id"])

            return redirect(payment_link.url)

        except stripe.error.StripeError:
            messages.error(
                request,
                _("Unable to create payment link. Please try again later."),
            )
            return redirect("accounts_profile")


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    """Confirmation page after successful payment.

    Supports two query-string shapes:
    - ``?session_id=<checkout_session_id>`` – from Stripe Payment Link redirect
    - ``?payment_intent=<pi_id>``            – legacy Stripe Elements flow
    """

    template_name = "events/payment_success.html"

    def _find_request_by_stripe_id(self, stripe_id):
        """Look up the session request by its stored Stripe identifier."""
        try:
            return PeerSessionRequest.objects.get(
                stripe_payment_intent_id=stripe_id,
                attendee=self.request.user,
            )
        except PeerSessionRequest.DoesNotExist:
            pass
        try:
            return GroupSessionRequest.objects.get(
                stripe_payment_intent_id=stripe_id,
                attendee=self.request.user,
            )
        except GroupSessionRequest.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Payment Link redirect sends the checkout session id
        checkout_session_id = self.request.GET.get("session_id")
        payment_intent_id = self.request.GET.get("payment_intent")

        session_request = None

        if checkout_session_id:
            try:
                stripe.api_key = get_stripe_secret_key(self.request)
                checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
                pi_id = checkout_session.get("payment_intent")
                if pi_id:
                    session_request = self._find_request_by_stripe_id(
                        checkout_session.get("metadata", {}).get("session_request_id")
                        or pi_id
                    )
                    # Also look up by our stored payment-link id
                    if not session_request:
                        session_request = self._find_request_by_stripe_id(
                            checkout_session.get("payment_link")
                        )
                    # Persist the real payment_intent on the request for refunds
                    if session_request and pi_id:
                        session_request.stripe_payment_intent_id = pi_id
                        session_request.save(update_fields=["stripe_payment_intent_id"])
            except stripe.error.StripeError:
                pass
        elif payment_intent_id:
            session_request = self._find_request_by_stripe_id(payment_intent_id)

        if session_request:
            context["session_request"] = session_request
            notify_payment_made(session_request)
            notify_payment_received(session_request)

            # Format the session for the session_item card component
            from apps.events.utils import format_session_for_card

            context["session_card"] = format_session_for_card(
                session_request.session, user=self.request.user
            )

        return context


class RequestRefundView(LoginRequiredMixin, View):
    """Request a refund for a paid session."""

    def post(self, request, request_id):
        session_request = _get_session_request(request_id, attendee=request.user)
        if session_request is None:
            messages.error(request, _("This request could not be found."))
            return redirect("accounts_user_settings")

        # Check if paid
        if not session_request.stripe_payment_intent_id:
            messages.error(request, "This session has not been paid for")
            return redirect("accounts_user_settings")

        # Check if already refunded
        if session_request.refunded:
            messages.info(request, "This session has already been refunded")
            return redirect("accounts_user_settings")

        # Check if refund requires approval
        if session_request.session.require_refund_approval:
            session_request.refund_status = SessionRequestStatusChoices.PENDING
            session_request.save(update_fields=["refund_status"])
            notify_refund_requested(session_request)
            messages.success(
                request,
                "Your refund request has been submitted and is pending approval",
            )
        else:
            # Automatic refund
            success = self._process_refund(session_request, request)
            if success:
                notify_refund_approved(session_request)
                messages.success(request, "Your refund has been processed")
            else:
                messages.error(request, "Refund failed. Please contact support.")

        return redirect("accounts_user_settings")

    def _process_refund(self, session_request, request):
        """Process the actual refund via Stripe."""
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
                return True

            return False

        except stripe.error.StripeError:
            return False


class ApproveRefundView(LoginRequiredMixin, View):
    """Host approves a refund request."""

    def post(self, request, request_id):
        session_request = _get_session_request(request_id, session__host=request.user)
        if session_request is None:
            messages.error(request, _("This request could not be found."))
            return redirect("accounts_user_settings")

        if session_request.refund_status != SessionRequestStatusChoices.PENDING:
            messages.error(request, "No pending refund request for this session")
            return redirect("accounts_user_settings")

        # Process refund
        success = self._process_refund(session_request, request)
        if success:
            notify_refund_approved(session_request)
            messages.success(request, "Refund has been approved and processed")
        else:
            messages.error(request, "Refund failed. Please contact support.")

        return redirect("accounts_user_settings")

    def _process_refund(self, session_request, request):
        """Process the actual refund via Stripe."""
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
                return True

            return False

        except stripe.error.StripeError:
            return False


class PaymentHistoryView(LoginRequiredMixin, ListView):
    """View payment history for a user."""

    template_name = "events/payment_history.html"
    context_object_name = "payments"
    paginate_by = 20

    def get_queryset(self):
        # Get all session requests with payments from both session types
        from itertools import chain

        peer = list(
            PeerSessionRequest.objects.filter(
                attendee=self.request.user,
                stripe_payment_intent_id__isnull=False,
            ).select_related("session", "session__host")
        )
        group = list(
            GroupSessionRequest.objects.filter(
                attendee=self.request.user,
                stripe_payment_intent_id__isnull=False,
            ).select_related("session", "session__host")
        )
        combined = sorted(chain(peer, group), key=lambda r: r.created_at, reverse=True)
        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.events.models_sessions.peer import PeerSessionRequest
        from apps.events.utils import format_session_for_card

        # Fetch payment details from Stripe
        stripe.api_key = get_stripe_secret_key(self.request)

        payments_with_details = []
        for payment in context["payments"]:
            try:
                intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
                payment.stripe_details = intent
            except stripe.error.StripeError:
                payment.stripe_details = None

            # Normalize fields across PeerSessionRequest / GroupSessionRequest
            is_peer = isinstance(payment, PeerSessionRequest)
            payment.display_price = (
                payment.price if is_peer else payment.session.price_display
            )
            payment.display_language = (
                payment.language_display
                if is_peer
                else payment.session.language_display
            )
            payment.display_starts_at = (
                payment.starts_at if is_peer else payment.session.starts_at
            )
            payment.display_ends_at = (
                payment.ends_at if is_peer else payment.session.ends_at
            )
            payment.session_card = format_session_for_card(
                payment.session, user=self.request.user
            )

            payments_with_details.append(payment)

        context["payments"] = payments_with_details
        return context


class ManageMeetingLinkView(LoginRequiredMixin, View):
    """Generate, regenerate, or remove a Whereby meeting link for a session.

    Only the session host can manage meeting links. For peer sessions the link
    is stored on the PeerSessionRequest; for group sessions it's on the
    GroupSession itself.
    """

    def post(self, request):
        from apps.events.utils import create_whereby_meeting

        request_id = request.POST.get("request_id")
        request_type = request.POST.get("request_type")
        link_action = request.POST.get("link_action")

        if not all([request_id, request_type, link_action]):
            messages.error(request, _("Invalid request."))
            return redirect("host_dashboard")

        # Look up the session request (host-only)
        session_request = _get_session_request(request_id, session__host=request.user)
        if not session_request:
            messages.error(request, _("Request not found."))
            return redirect("host_dashboard")

        # Determine which object holds the meeting link
        if request_type == "group":
            link_obj = session_request.session  # GroupSession
            start_time = session_request.session.starts_at
            end_time = session_request.session.ends_at
        else:
            link_obj = session_request  # PeerSessionRequest
            start_time = session_request.starts_at
            end_time = session_request.ends_at

        if link_action == "remove":
            link_obj.meeting_link = ""
            link_obj.save(update_fields=["meeting_link"])
            messages.success(request, _("Meeting link removed."))
        elif link_action in ("generate", "regenerate"):
            meeting = create_whereby_meeting(
                start_time,
                end_time,
                room_name_prefix=session_request.session.title[:30],
                request=request,
            )
            if meeting and meeting.get("roomUrl"):
                link_obj.meeting_link = meeting["roomUrl"]
                link_obj.save(update_fields=["meeting_link"])
                messages.success(request, _("Meeting link generated."))
            else:
                messages.error(
                    request,
                    _("Could not generate a meeting link. Please try again."),
                )

        tab = "peer" if request_type == "peer" else "group"
        return redirect(f"{reverse('host_dashboard')}?tab={tab}")


# Calendar export views
class CalendarExportView(LoginRequiredMixin, View):
    """Export user's sessions to ICS format."""

    def get(self, request):
        from apps.events.calendar_export import create_ics_response
        from apps.events.models import GroupSession, GroupSessionRequest

        events = []

        # Get peer session requests (as attendee)
        peer_requests = PeerSessionRequest.objects.filter(
            attendee=request.user,
            status=SessionRequestStatusChoices.APPROVED,
        ).select_related("session", "session__host")

        for req in peer_requests:
            events.append(
                {
                    "uid": f"peer-request-{req.id}@neuromancers",
                    "title": req.session.title,
                    "description": f"Peer session with {req.session.host}",
                    "start": req.starts_at,
                    "end": req.ends_at,
                    "organizer": str(req.session.host),
                }
            )

        # Get peer sessions (as host)
        peer_hosted = PeerSessionRequest.objects.filter(
            session__host=request.user,
            status=SessionRequestStatusChoices.APPROVED,
        ).select_related("session", "attendee")

        for req in peer_hosted:
            events.append(
                {
                    "uid": f"peer-hosted-{req.id}@neuromancers",
                    "title": f"{req.session.title} (Hosting)",
                    "description": f"Peer session with {req.attendee}",
                    "start": req.starts_at,
                    "end": req.ends_at,
                }
            )

        # Get group session requests (as attendee)
        group_requests = GroupSessionRequest.objects.filter(
            attendee=request.user,
            status=SessionRequestStatusChoices.APPROVED,
        ).select_related("session", "session__host")

        for req in group_requests:
            events.append(
                {
                    "uid": f"group-request-{req.id}@neuromancers",
                    "title": req.session.title,
                    "description": f"Group session hosted by {req.session.host}",
                    "start": req.session.starts_at,
                    "end": req.session.ends_at,
                    "organizer": str(req.session.host),
                }
            )

        # Get group sessions (as host)
        group_hosted = GroupSession.objects.filter(
            host=request.user,
            is_published=True,
        )

        for session in group_hosted:
            events.append(
                {
                    "uid": f"group-hosted-{session.id}@neuromancers",
                    "title": f"{session.title} (Hosting)",
                    "description": f"Group session - {session.capacity} capacity",
                    "start": session.starts_at,
                    "end": session.ends_at,
                }
            )

        return create_ics_response(events, filename="my-sessions.ics")


class SessionCalendarExportView(View):
    """Export a single session to various calendar formats."""

    def get(self, request, session_type, session_id):
        from django.http import JsonResponse

        from apps.events.calendar_export import (
            create_ics_response,
            get_google_calendar_url,
            get_outlook_calendar_url,
            get_yahoo_calendar_url,
        )
        from apps.events.models import GroupSession, PeerSessionRequest

        format_type = request.GET.get("format", "ics")

        # Get session data
        if session_type == "peer":
            # For peer sessions, we need a specific request
            request_id = request.GET.get("request_id")
            if not request_id:
                return JsonResponse(
                    {"error": "request_id required for peer sessions"}, status=400
                )

            obj = get_object_or_404(PeerSessionRequest, pk=request_id)
            title = obj.session.title
            description = obj.session.description or ""
            start = obj.starts_at
            end = obj.ends_at
            uid = f"peer-{obj.id}@neuromancers"

        elif session_type == "group":
            obj = get_object_or_404(GroupSession, pk=session_id)
            title = obj.title
            description = obj.description or ""
            start = obj.starts_at
            end = obj.ends_at
            uid = f"group-{obj.id}@neuromancers"
        else:
            return JsonResponse({"error": "Invalid session type"}, status=400)

        if format_type == "google":
            url = get_google_calendar_url(title, start, end, description)
            return redirect(url)
        elif format_type == "outlook":
            url = get_outlook_calendar_url(title, start, end, description)
            return redirect(url)
        elif format_type == "yahoo":
            url = get_yahoo_calendar_url(title, start, end, description)
            return redirect(url)
        else:
            # Default to ICS download
            events = [
                {
                    "uid": uid,
                    "title": title,
                    "description": description,
                    "start": start,
                    "end": end,
                }
            ]
            filename = f"session-{session_id}.ics"
            return create_ics_response(events, filename=filename)
