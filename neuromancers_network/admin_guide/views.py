import django_filters
from django.contrib import messages
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from wagtail.admin.panels import Component
from wagtail.admin.panels import FieldPanel
from wagtail.admin.views.generic import WagtailAdminTemplateMixin
from wagtail.admin.viewsets.model import ModelViewSet

from .models import Guide
from .models import OnboardingTask


class GuideFilterSet(django_filters.FilterSet):
    tags = django_filters.CharFilter(
        field_name="tags__name",
        lookup_expr="icontains",
        label=_("Tags"),
    )

    class Meta:
        model = Guide
        fields = ["topic", "tags"]


class GuideViewSet(ModelViewSet):
    model = Guide

    icon = "pick"

    menu_label = _("Admin Guide")

    menu_name = "admin_guide"

    add_to_admin_menu = True

    inspect_view_enabled = True

    list_display = [
        "title",
        "slug",
        "topic",
        "live",
    ]

    filterset_class = GuideFilterSet

    search_fields = [
        "title",
        "summary",
        "content",
    ]

    ordering = ["topic", "title"]

    panels = Guide.panels


class OnboardingTaskViewSet(ModelViewSet):
    model = OnboardingTask

    menu_label = "Onboarding"

    menu_name = "onboarding"

    icon = "tick-inverse"

    add_to_admin_menu = False

    inspect_view_enabled = True

    copy_view_enabled = False

    delete_view_enabled = False

    list_display = [
        "title",
        "completed",
    ]

    ordering = ["sort_order"]

    panels = [
        FieldPanel("completed"),
    ]

    exclude_form_fields = [
        "title",
        "slug",
        "description",
        "sort_order",
    ]


class OnboardingTaskPanel(Component):
    order = 50

    def render_html(self, parent_context):
        return render_to_string(
            "admin_guide/onboarding_panel.html",
            {
                "tasks": OnboardingTask.objects.order_by("sort_order"),
            },
        )


class StripeSyncView(WagtailAdminTemplateMixin, TemplateView):
    template_name = "admin_guide/stripe_sync.html"
    page_title = _("Manual Stripe Sync")
    header_icon = "cogs"

    def get(self, request):
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["messages"] = messages.get_messages(self.request)
        return context

    def post(self, request):
        model_name = request.POST.get("model_type")
        stripe_id = request.POST.get("stripe_id", "").strip()

        if not model_name or not stripe_id:
            messages.error(request, "Both model type and Stripe ID are required.")
            return redirect(self.get_url())

        model_map = {
            "Product": "djstripe.Product",
            "Price": "djstripe.Price",
            "Customer": "djstripe.Customer",
            "Session": "djstripe.Session",
            "Subscription": "djstripe.Subscription",
            "Invoice": "djstripe.Invoice",
            "PaymentIntent": "djstripe.PaymentIntent",
            "Charge": "djstripe.Charge",
            "Account": "djstripe.Account",
            "PromotionCode": "djstripe.PromotionCode",
            "Coupon": "djstripe.Coupon",
        }

        dotted = model_map.get(model_name)
        if not dotted:
            messages.error(request, f"Unknown model type: {model_name}")
            return redirect(self.get_url())

        try:
            from django.apps import apps

            app_label, model_cls_name = dotted.split(".")
            model_cls = apps.get_model(app_label, model_cls_name)
        except Exception:
            messages.error(request, f"Could not load model: {model_name}")
            return redirect(self.get_url())

        stripe_resource_map = {
            "Product": "product",
            "Price": "price",
            "Customer": "customer",
            "Session": "checkout.session",
            "Subscription": "subscription",
            "Invoice": "invoice",
            "PaymentIntent": "payment_intent",
            "Charge": "charge",
            "Account": "account",
            "PromotionCode": "promotion_code",
            "Coupon": "coupon",
        }

        resource_name = stripe_resource_map.get(model_name)
        if not resource_name:
            messages.error(request, f"No Stripe resource mapping for: {model_name}")
            return redirect(self.get_url())

        try:
            import stripe
            from django.conf import settings

            stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

            if "." in resource_name:
                parts = resource_name.split(".")
                resource = getattr(stripe, parts[0])
                for part in parts[1:]:
                    resource = getattr(resource, part)
            else:
                resource = getattr(stripe, resource_name)

            data = resource.retrieve(stripe_id)
            obj = model_cls.sync_from_stripe_data(data)
            messages.success(
                request,
                f"Synced {model_name} {stripe_id} successfully (pk={obj.pk}).",
            )
        except Exception as e:
            messages.error(request, f"Sync failed: {e}")

        return redirect(self.get_url())

    def get_url(self):
        return reverse("admin_guide_stripe_sync")
