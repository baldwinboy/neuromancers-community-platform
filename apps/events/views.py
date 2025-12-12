"""
Stripe payment and refund views for session requests.
"""

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.common.utils import get_stripe_secret_key
from apps.events.choices import SessionRequestStatusChoices
from apps.events.models import PeerSessionRequest


class CreatePaymentIntentView(LoginRequiredMixin, View):
    """Create a Stripe Payment Intent for a session request."""

    def post(self, request, request_id):
        session_request = get_object_or_404(
            PeerSessionRequest, pk=request_id, attendee=request.user
        )

        # Check if already paid
        if session_request.stripe_payment_intent_id:
            return JsonResponse(
                {"error": "This session has already been paid for"}, status=400
            )

        # Check if approved
        if session_request.status != SessionRequestStatusChoices.APPROVED:
            return JsonResponse(
                {"error": "This session request must be approved before payment"},
                status=400,
            )

        # Calculate amount
        duration_hrs = (
            session_request.ends_at - session_request.starts_at
        ).total_seconds() / 3600

        if session_request.pay_concessionary_price:
            if session_request.session.concessionary_per_hour_price:
                amount = int(
                    duration_hrs * session_request.session.concessionary_per_hour_price
                )
            else:
                amount = session_request.session.concessionary_price or 0
        else:
            if session_request.session.per_hour_price:
                amount = int(duration_hrs * session_request.session.per_hour_price)
            else:
                amount = session_request.session.price or 0

        if amount <= 0:
            return JsonResponse(
                {"error": "This is a free session, no payment required"}, status=400
            )

        try:
            stripe.api_key = get_stripe_secret_key(request)

            # Calculate application fee (15%)
            application_fee = int(amount * settings.STRIPE_APPLICATION_FEE)

            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=session_request.session.currency.lower(),
                application_fee_amount=application_fee,
                transfer_data={
                    "destination": session_request.session.host.stripe_account.id,
                },
                metadata={
                    "session_request_id": str(session_request.id),
                    "session_title": session_request.session.title,
                    "attendee_id": str(request.user.id),
                },
            )

            # Save payment intent ID
            session_request.stripe_payment_intent_id = intent.id
            session_request.save(update_fields=["stripe_payment_intent_id"])

            return JsonResponse(
                {
                    "clientSecret": intent.client_secret,
                    "paymentIntentId": intent.id,
                }
            )

        except stripe.error.StripeError as e:
            return JsonResponse({"error": str(e)}, status=400)


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    """Confirmation page after successful payment."""

    template_name = "events/payment_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        payment_intent_id = self.request.GET.get("payment_intent")
        if payment_intent_id:
            try:
                session_request = PeerSessionRequest.objects.get(
                    stripe_payment_intent_id=payment_intent_id,
                    attendee=self.request.user,
                )
                context["session_request"] = session_request
            except PeerSessionRequest.DoesNotExist:
                pass

        return context


class RequestRefundView(LoginRequiredMixin, View):
    """Request a refund for a paid session."""

    def post(self, request, request_id):
        session_request = get_object_or_404(
            PeerSessionRequest, pk=request_id, attendee=request.user
        )

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
            messages.success(
                request,
                "Your refund request has been submitted and is pending approval",
            )
        else:
            # Automatic refund
            success = self._process_refund(session_request, request)
            if success:
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
        session_request = get_object_or_404(
            PeerSessionRequest, pk=request_id, session__host=request.user
        )

        if session_request.refund_status != SessionRequestStatusChoices.PENDING:
            messages.error(request, "No pending refund request for this session")
            return redirect("accounts_user_settings")

        # Process refund
        success = self._process_refund(session_request, request)
        if success:
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
        # Get all session requests with payments
        return (
            PeerSessionRequest.objects.filter(
                attendee=self.request.user, stripe_payment_intent_id__isnull=False
            )
            .select_related("session", "session__host")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch payment details from Stripe
        stripe.api_key = get_stripe_secret_key(self.request)

        payments_with_details = []
        for payment in context["payments"]:
            try:
                intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
                payment.stripe_details = intent
            except stripe.error.StripeError:
                payment.stripe_details = None

            payments_with_details.append(payment)

        context["payments"] = payments_with_details
        return context
