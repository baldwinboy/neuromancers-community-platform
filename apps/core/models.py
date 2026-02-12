from django.db import models
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page

from .blocks import (
    CTABlock,
    FAQBlock,
    FeatureGridBlock,
    GridBlock,
    HeroBlock,
    MarqueeBlock,
    SpacerBlock,
    TestimonialBlock,
    TextBlock,
    TextImageBlock,
)


def get_shared_streamfield_blocks():
    """
    Returns the shared StreamField block types used across multiple page types.
    Use this to ensure consistency between HomePage, BlogIndexPage, ContactFormPage, etc.
    """
    return [
        ("hero", HeroBlock()),
        ("text", TextBlock()),
        ("text_image", TextImageBlock()),
        ("cta", CTABlock()),
        ("testimonial", TestimonialBlock()),
        ("features", FeatureGridBlock()),
        ("faq", FAQBlock()),
        ("spacer", SpacerBlock()),
        ("grid", GridBlock()),
        ("marquee", MarqueeBlock()),
    ]


class HomePage(Page):
    max_count = 1

    body = StreamField(
        get_shared_streamfield_blocks(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Build your page by adding blocks",
    )

    subpage_types = [
        "events.SessionsIndexPage",
        "contact.ContactFormPage",
        "blog.BlogIndexPage",
    ]

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]


@register_setting(icon="link")
class Links(BaseGenericSetting):
    terms_and_conditions = models.URLField(
        help_text="Your organisation's terms and conditions URL"
    )


@register_setting(icon="mail")
class EmailTemplateSettings(BaseGenericSetting):
    """
    Customizable text content for notification emails.

    Each email type has a greeting, main message, and closing message
    that can be customized by admins without editing templates.
    """

    # Account Created Email
    account_created_greeting = RichTextField(
        default="Your account has been created successfully. Welcome to our community!",
        help_text="Greeting text for account creation notification",
    )
    account_created_body = RichTextField(
        default="Start by exploring sessions, connecting with peers, or setting up your profile. If you have any questions, our support team is here to help.",
        help_text="Main body text for account creation notification",
    )

    # Account Closed Email
    account_closed_greeting = RichTextField(
        default="We're sorry to see you go. Your account has been closed as requested.",
        help_text="Greeting text for account closure notification",
    )
    account_closed_body = RichTextField(
        default="If you have any questions about your account closure or need to retrieve any information, please contact our support team within 30 days of this notice.",
        help_text="Main body text for account closure notification",
    )
    account_closed_note = RichTextField(
        default="We hope to see you in the community again someday!",
        help_text="Closing note for account closure notification",
    )

    # Group Status Changed Email
    group_upgrade_greeting = RichTextField(
        default="Congratulations! You've been upgraded to a Peer in the Neuromancers community.",
        help_text="Greeting text when user is upgraded to Peer",
    )
    group_upgrade_body = RichTextField(
        default="As a Peer, you can now create sessions and share your expertise with support seekers. Complete your profile and set up your session offerings to get started.",
        help_text="Main body text for Peer upgrade notification",
    )
    group_downgrade_greeting = RichTextField(
        default="Your account role has been updated.",
        help_text="Greeting text when user role changes (general)",
    )
    group_downgrade_body = RichTextField(
        default="Your role has been updated in our community. Please review your account settings to see what features are available to you.",
        help_text="Main body text for general role change notification",
    )

    # Session Published Email
    session_published_greeting = RichTextField(
        default="Congratulations! Your session has been published.",
        help_text="Greeting text for session published notification (shown to host)",
    )
    session_published_body = RichTextField(
        default="Your session is now visible to support seekers. Support seekers can now request sessions with you. Check your notifications regularly for new requests.",
        help_text="Main body text for session published notification",
    )

    # Session Requested Email
    session_requested_greeting = RichTextField(
        default="A support seeker has requested to book your session.",
        help_text="Greeting text for session request notification (shown to host)",
    )
    session_requested_body = RichTextField(
        default="Review this request and either approve or decline it.",
        help_text="Main body text for session request notification",
    )

    # Session Approved Email
    session_approved_greeting = RichTextField(
        default="Great news! Your request has been approved.",
        help_text="Greeting text for session approval notification (shown to seeker)",
    )
    session_approved_body = RichTextField(
        default="Your session is now confirmed. Please arrive a few minutes early. If you have any questions, reach out to your host.",
        help_text="Main body text for session approval notification",
    )

    # Payment Made Email
    payment_made_greeting = RichTextField(
        default="Thank you for your payment! Your session is now confirmed.",
        help_text="Greeting text for payment confirmation (shown to seeker)",
    )
    payment_made_body = RichTextField(
        default="Your payment has been securely processed through Stripe. You'll receive a separate confirmation email from Stripe with your receipt.",
        help_text="Main body text for payment confirmation",
    )

    # Payment Received Email
    payment_received_greeting = RichTextField(
        default="You've received a payment for your session!",
        help_text="Greeting text for payment received notification (shown to host)",
    )
    payment_received_body = RichTextField(
        default="The payment has been processed and transferred to your connected Stripe account. You can view your payment history and balance in your account dashboard.",
        help_text="Main body text for payment received notification",
    )

    # Refund Requested Email
    refund_requested_greeting = RichTextField(
        default="A support seeker has requested a refund for their session payment.",
        help_text="Greeting text for refund request notification (shown to host)",
    )
    refund_requested_body = RichTextField(
        default="Please review this request and decide whether to approve or decline the refund. You can manage this in your account.",
        help_text="Main body text for refund request notification",
    )
    refund_requested_note = RichTextField(
        default="Note: You're not required to approve this refund, but doing so helps maintain a positive experience for support seekers.",
        help_text="Note text shown at end of refund request notification",
    )

    # Refund Approved Email
    refund_approved_greeting = RichTextField(
        default="Good news! Your refund request has been approved.",
        help_text="Greeting text for refund approval notification (shown to seeker)",
    )
    refund_approved_body = RichTextField(
        default="We appreciate your understanding. If you have any feedback about your experience, we'd love to hear from you.",
        help_text="Main body text for refund approval notification",
    )

    panels = [
        TabbedInterface(
            [
                ObjectList(
                    [
                        FieldPanel("account_created_greeting"),
                        FieldPanel("account_created_body"),
                    ],
                    heading="Account Created",
                ),
                ObjectList(
                    [
                        FieldPanel("account_closed_greeting"),
                        FieldPanel("account_closed_body"),
                        FieldPanel("account_closed_note"),
                    ],
                    heading="Account Closed",
                ),
                ObjectList(
                    [
                        FieldPanel("group_upgrade_greeting"),
                        FieldPanel("group_upgrade_body"),
                        FieldPanel("group_downgrade_greeting"),
                        FieldPanel("group_downgrade_body"),
                    ],
                    heading="Group Status Changed",
                ),
                ObjectList(
                    [
                        FieldPanel("session_published_greeting"),
                        FieldPanel("session_published_body"),
                    ],
                    heading="Session Published",
                ),
                ObjectList(
                    [
                        FieldPanel("session_requested_greeting"),
                        FieldPanel("session_requested_body"),
                    ],
                    heading="Session Requested",
                ),
                ObjectList(
                    [
                        FieldPanel("session_approved_greeting"),
                        FieldPanel("session_approved_body"),
                    ],
                    heading="Session Approved",
                ),
                ObjectList(
                    [
                        FieldPanel("payment_made_greeting"),
                        FieldPanel("payment_made_body"),
                    ],
                    heading="Payment Made",
                ),
                ObjectList(
                    [
                        FieldPanel("payment_received_greeting"),
                        FieldPanel("payment_received_body"),
                    ],
                    heading="Payment Received",
                ),
                ObjectList(
                    [
                        FieldPanel("refund_requested_greeting"),
                        FieldPanel("refund_requested_body"),
                        FieldPanel("refund_requested_note"),
                    ],
                    heading="Refund Requested",
                ),
                ObjectList(
                    [
                        FieldPanel("refund_approved_greeting"),
                        FieldPanel("refund_approved_body"),
                    ],
                    heading="Refund Approved",
                ),
            ]
        )
    ]

    class Meta:
        verbose_name = "Email Templates"
