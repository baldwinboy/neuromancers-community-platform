"""Seed and clean deterministic demo/test data for manual testing."""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection
from django.db import transaction
from django.test import override_settings
from django.utils import timezone
from wagtail.coreutils import find_available_slug

logger = logging.getLogger(__name__)

DEMO_PREFIX = "demo-"
DEMO_TITLE_PREFIX = "DEMO — "
DEMO_TAG_GROUP_SLUG = "demo-data"
DEMO_REQUEST_START_DAYS = 1
DEMO_MEETING_PRICE = Decimal("25.00")
DEMO_EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


class DemoDataError(Exception):
    """A demo-data operation cannot proceed."""


def parse_demo_email_base(value: str) -> tuple[str, str]:
    """Return the normalised ``(local, domain)`` base email parts."""
    value = (value or "").strip()
    try:
        validate_email(value)
    except ValidationError as exc:
        msg = "Enter a valid base email address."
        raise DemoDataError(msg) from exc
    local, domain = value.rsplit("@", 1)
    local = local.split("+", 1)[0].strip().lower()
    domain = domain.strip().lower()
    if not local or not domain:
        msg = "Enter a valid base email address."
        raise DemoDataError(msg)
    return local, domain


def demo_email(local: str, domain: str, username: str) -> str:
    """Return ``local+username@domain`` for a demo account."""
    return f"{local}+{username}@{domain}".lower()


def validate_test_stripe_keys() -> None:
    """Require configured Stripe test/sandbox key prefixes."""
    from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415

    config = StripeSettings.load()
    secret = config.secret_key or ""
    publishable = config.publishable_key or ""

    if not config.is_ready:
        msg = "Configure both Stripe publishable and secret keys before seeding."
        raise DemoDataError(
            msg,
        )
    if secret.startswith(("sk_live_", "rk_live_")):
        msg = "Demo data cannot run with live Stripe keys."
        raise DemoDataError(msg)
    if not secret.startswith(("sk_test_", "rk_test_")):
        msg = "The Stripe secret key must be a test/sandbox key."
        raise DemoDataError(msg)
    if not publishable.startswith("pk_test_"):
        msg = "The Stripe publishable key must be a test/sandbox key."
        raise DemoDataError(
            msg,
        )


def _user_model():
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    return get_user_model()


def _demo_users(email_base: str | None = None):
    users = _user_model().objects.filter(username__startswith=DEMO_PREFIX)
    if email_base:
        local, domain = parse_demo_email_base(email_base)
        users = users.filter(
            email__istartswith=f"{local}+demo-",
            email__iendswith=f"@{domain}",
        )
    return users


def _demo_meetings(users):
    from django.db.models import Q  # noqa: PLC0415

    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415

    return Meeting.objects.filter(
        Q(peer__in=users) | Q(title__startswith=DEMO_TITLE_PREFIX),
    )


def _email_bases(users) -> list[str]:
    bases = set()
    for email in users.values_list("email", flat=True):
        if not email or "@" not in email:
            continue
        local, domain = email.rsplit("@", 1)
        bases.add(f"{local.split('+', 1)[0]}@{domain}")
    return sorted(bases)


def demo_data_status(email_base: str | None = None) -> dict:
    """Return counts and detected demo email bases."""
    from neuromancers_network.inbox.models import Notification  # noqa: PLC0415
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
    from neuromancers_network.meetings.models import RefundRequest  # noqa: PLC0415
    from neuromancers_network.meetings.models import Review  # noqa: PLC0415
    from neuromancers_network.peers.models import PeerProfile  # noqa: PLC0415

    users = _demo_users(email_base)
    meetings = _demo_meetings(users)
    return {
        "users": users.count(),
        "peers": PeerProfile.objects.filter(user__in=users).count(),
        "seekers": users.filter(peer_profile__isnull=True).count(),
        "meetings": meetings.count(),
        "bookings": Booking.objects.filter(meeting__in=meetings).count(),
        "requests": MeetingRequest.objects.filter(meeting__in=meetings).count(),
        "reviews": Review.objects.filter(peer__in=users).count(),
        "refunds": RefundRequest.objects.filter(
            meeting_request__meeting__in=meetings,
        ).count(),
        "notifications": Notification.objects.filter(recipient__in=users).count(),
        "email_bases": _email_bases(_demo_users()),
    }


def _advisory_lock() -> None:
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            ["neuromancers-network-demo-data"],
        )


def _home_page():
    from neuromancers_network.core.models import HomePage  # noqa: PLC0415

    home = HomePage.objects.live().first() or HomePage.objects.first()
    if home is None:
        msg = "No HomePage found. Run the chrome/page seed first."
        raise DemoDataError(msg)
    return home


def _ensure_child(home, page_class, slug: str, title: str, **fields):
    page = page_class.objects.child_of(home).order_by("path").first()
    if page is not None:
        return page
    page = page_class(
        title=title,
        slug=find_available_slug(home, slug),
        **fields,
    )
    home.add_child(instance=page)
    page.save_revision().publish()
    return page


def _ensure_pages(home) -> None:
    from neuromancers_network.core.models.pages import BookingDetailTemplate  # noqa: PLC0415
    from neuromancers_network.core.models.pages import MeetingIndexPage  # noqa: PLC0415
    from neuromancers_network.core.models.pages import PeerIndexPage  # noqa: PLC0415
    from neuromancers_network.core.models.pages import RefundRequestDetailTemplate  # noqa: PLC0415
    from neuromancers_network.core.models.pages import ReviewIndexPage  # noqa: PLC0415
    from neuromancers_network.core.models.pages import TagIndexPage  # noqa: PLC0415

    pages = (
        (MeetingIndexPage, "meetings", "Meetings", {}),
        (PeerIndexPage, "peers", "Care providers", {}),
        (ReviewIndexPage, "reviews", "Reviews", {}),
        (TagIndexPage, "tags", "Tags", {}),
        (
            BookingDetailTemplate,
            "booking-detail",
            "Booking detail",
            {"detail_key": "booking"},
        ),
        (
            RefundRequestDetailTemplate,
            "refund-detail",
            "Refund detail",
            {"detail_key": "refund_request"},
        ),
    )
    for page_class, slug, title, fields in pages:
        _ensure_child(home, page_class, slug, title, **fields)


def _ensure_taxonomy():
    from neuromancers_network.taxonomy.models import AllowedTag  # noqa: PLC0415
    from neuromancers_network.taxonomy.models import Country  # noqa: PLC0415
    from neuromancers_network.taxonomy.models import Language  # noqa: PLC0415
    from neuromancers_network.taxonomy.models import TagGroup  # noqa: PLC0415

    country, _ = Country.objects.get_or_create(
        code="GB",
        defaults={"name": "United Kingdom"},
    )
    language, _ = Language.objects.get_or_create(
        code="en",
        defaults={"name": "English", "name_local": "English"},
    )
    group, _ = TagGroup.objects.get_or_create(
        slug=DEMO_TAG_GROUP_SLUG,
        defaults={"name": "Demo data"},
    )
    tag, _ = AllowedTag.objects.get_or_create(
        group=group,
        name="demo-support",
        defaults={"description": "Demo/test tag"},
    )
    return country, language, tag


def _seed_user(*, username: str, email: str, name: str, password: str, bio: str):
    from allauth.account.models import EmailAddress  # noqa: PLC0415

    from neuromancers_network.users.models import UserProfile  # noqa: PLC0415
    from neuromancers_network.users.services import sync_email_address  # noqa: PLC0415

    user_model = _user_model()
    user, _created = user_model.objects.get_or_create(
        username=username,
        defaults={"email": email},
    )
    user.email = email
    user.name = name
    user.is_active = True
    user.accepted_tos = True
    user.set_password(password)
    user.save()
    address = sync_email_address(user)
    if address is not None:
        address.set_verified()
        address.set_as_primary()
        EmailAddress.objects.filter(user=user, primary=True).exclude(
            pk=address.pk,
        ).update(primary=False)
    UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "bio": bio,
            "country": "GB",
            "timezone": "UTC",
            "show_calendar": True,
        },
    )
    return user


def _seed_local_stripe(user, *, slug: str, paused_at=None):
    from djstripe.models import Account as StripeAccount  # noqa: PLC0415
    from djstripe.models import Customer as StripeCustomer  # noqa: PLC0415
    from djstripe.models import Subscription as StripeSubscription  # noqa: PLC0415

    from neuromancers_network.payments.models import PaymentProfile  # noqa: PLC0415
    from neuromancers_network.peers.models import PeerSubscription  # noqa: PLC0415

    customer, _ = StripeCustomer.objects.update_or_create(
        id=f"cus_demo_{slug}",
        defaults={"livemode": False},
    )
    account, _ = StripeAccount.objects.update_or_create(
        id=f"acct_demo_{slug}",
        defaults={"livemode": False},
    )
    subscription, _ = StripeSubscription.objects.update_or_create(
        id=f"sub_demo_{slug}",
        defaults={
            "customer": customer,
            "livemode": False,
            "stripe_data": {"status": "active"},
        },
    )
    payment_profile, _ = PaymentProfile.objects.update_or_create(
        user=user,
        defaults={
            "stripe_customer_id": customer,
            "stripe_connect_account_id": account,
            "kyc_completed": True,
        },
    )
    PeerSubscription.objects.update_or_create(
        payment_profile=payment_profile,
        defaults={"subscription": subscription, "paused_at": paused_at},
    )
    return payment_profile


def _seed_peer(  # noqa: PLR0913
    *,
    username,
    email,
    name,
    password,
    country,
    language,
    tag,
    paused=False,
):
    from neuromancers_network.peers.models import PeerApplication  # noqa: PLC0415
    from neuromancers_network.peers.models import PeerApplicationStatus  # noqa: PLC0415
    from neuromancers_network.peers.models import PeerProfile  # noqa: PLC0415

    user = _seed_user(
        username=username,
        email=email,
        name=name,
        password=password,
        bio=f"{name} is a demo care provider.",
    )
    now = timezone.now()
    profile, _ = PeerProfile.objects.update_or_create(
        user=user,
        defaults={
            "bio": f"{name} is a demo care provider.",
            "default_terms": "Demo terms for testing.",
            "provider_agreement_accepted_at": now,
            "provider_agreement_version": "1",
            "is_approved": True,
            "approved_at": now,
            "is_verified": True,
            "verified_at": now,
        },
    )
    profile.languages.set([language])
    profile.countries.set([country])
    profile.tags.add(tag)
    PeerApplication.objects.update_or_create(
        user=user,
        defaults={
            "reason": "Demo application for testing.",
            "is_approved": True,
            "status": PeerApplicationStatus.APPROVED,
            "reviewed_at": now,
            "submission": {"reason": "Demo application for testing."},
        },
    )
    _seed_local_stripe(user, slug=username, paused_at=now if paused else None)
    return user


def _seed_seeker(*, username, email, name, password, country, language):  # noqa: PLR0913
    user = _seed_user(
        username=username,
        email=email,
        name=name,
        password=password,
        bio=f"{name} is a demo support seeker.",
    )
    profile = user.user_profile
    profile.languages.set([language])
    profile.country = country.code
    profile.save(update_fields=["country", "updated_at"])
    return user


def _ensure_meeting(*, peer, title, meeting_type, approval_policy, **kwargs):
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415

    meeting = Meeting.objects.filter(peer=peer, title=title).first()
    if meeting is None:
        meeting = Meeting(
            peer=peer,
            title=title,
            description=f"{title} — demo meeting.",
            meeting_type=meeting_type,
            approval_policy=approval_policy,
            currency="GBP",
            status=MeetingStatus.PUBLISHED,
            **kwargs,
        )
    else:
        for key, value in kwargs.items():
            setattr(meeting, key, value)
        meeting.status = MeetingStatus.PUBLISHED
    meeting.save(validate=False)
    return meeting


def _ensure_booking(*, meeting, seeker, status, session_id, amount):
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415

    booking = Booking.objects.filter(stripe_checkout_session_id=session_id).first()
    if booking is None:
        booking = Booking(
            meeting=meeting,
            support_seeker=seeker,
            status=status,
            total_amount=amount,
            currency=meeting.currency,
            stripe_checkout_session_id=session_id,
            stripe_payment_intent_id=f"pi_{session_id}",
        )
    else:
        booking.meeting = meeting
        booking.support_seeker = seeker
        booking.status = status
        booking.total_amount = amount
        booking.currency = meeting.currency
    booking.save()
    return booking


def _ensure_request(*, booking, start, status, amount, session_id):
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    request = MeetingRequest.objects.filter(
        booking=booking,
        requested_start_time=start,
    ).first()
    if request is None:
        request = MeetingRequest(
            meeting=booking.meeting,
            support_seeker=booking.support_seeker,
            booking=booking,
            requested_start_time=start,
            requested_duration_minutes=60,
            status=status,
            price_paid=amount,
            price_paid_currency=booking.currency,
            stripe_checkout_session_id=session_id,
            stripe_payment_intent_id=f"pi_{session_id}",
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
    else:
        request.status = status
        request.price_paid = amount
        request.price_paid_currency = booking.currency
    request.save(validate=False)
    return request


def _seed_activity(*, peer, seekers, language, country, tag, paused=False):  # noqa: PLR0913
    from neuromancers_network.meetings.models import ApprovalPolicy  # noqa: PLC0415
    from neuromancers_network.meetings.models import BookingStatus  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequestStatus  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingType  # noqa: PLC0415
    from neuromancers_network.meetings.models import PricingType  # noqa: PLC0415
    from neuromancers_network.meetings.models import RefundRequest  # noqa: PLC0415
    from neuromancers_network.meetings.models import RefundStatus  # noqa: PLC0415
    from neuromancers_network.meetings.models import Review  # noqa: PLC0415
    from neuromancers_network.meetings.models import ReviewStatus  # noqa: PLC0415

    if paused:
        return 0

    one_to_one = _ensure_meeting(
        peer=peer,
        title=f"{DEMO_TITLE_PREFIX}1:1 with {peer.username}",
        meeting_type=MeetingType.ONE_ON_ONE,
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        pricing_type=PricingType.FIXED,
        price=DEMO_MEETING_PRICE,
    )
    one_to_one.languages.set([language])
    one_to_one.countries.set([country])
    one_to_one.tags.add(tag)

    group = _ensure_meeting(
        peer=peer,
        title=f"{DEMO_TITLE_PREFIX}Group with {peer.username}",
        meeting_type=MeetingType.GROUP,
        approval_policy=ApprovalPolicy.PAY_BEFORE_JOIN,
        pricing_type=PricingType.FIXED,
        price=Decimal("10.00"),
        scheduled_at=timezone.now() + timedelta(days=3),
        duration_minutes=60,
        max_participants=10,
    )
    group.languages.set([language])
    group.countries.set([country])
    group.tags.add(tag)

    approval_meeting = _ensure_meeting(
        peer=peer,
        title=f"{DEMO_TITLE_PREFIX}Approval with {peer.username}",
        meeting_type=MeetingType.ONE_ON_ONE,
        approval_policy=ApprovalPolicy.APPROVAL_REQUIRED,
        pricing_type=PricingType.FIXED,
        price=DEMO_MEETING_PRICE,
    )
    approval_meeting.languages.set([language])
    approval_meeting.countries.set([country])
    approval_meeting.tags.add(tag)

    seeker_a, seeker_b = seekers
    base = one_to_one.created_at + timedelta(days=DEMO_REQUEST_START_DAYS)
    booking = _ensure_booking(
        meeting=one_to_one,
        seeker=seeker_a,
        status=BookingStatus.PAID,
        session_id=f"cs_demo_paid_{peer.username}",
        amount=DEMO_MEETING_PRICE,
    )
    request = _ensure_request(
        booking=booking,
        start=base,
        status=MeetingRequestStatus.COMPLETED,
        amount=DEMO_MEETING_PRICE,
        session_id=booking.stripe_checkout_session_id,
    )
    Review.objects.update_or_create(
        meeting_request=request,
        defaults={
            "reviewer": seeker_a,
            "peer": peer,
            "rating": 5,
            "comment": "Demo review — excellent support.",
            "status": ReviewStatus.PUBLISHED,
        },
    )

    booking_b = _ensure_booking(
        meeting=one_to_one,
        seeker=seeker_b,
        status=BookingStatus.PAID,
        session_id=f"cs_demo_refund_{peer.username}",
        amount=DEMO_MEETING_PRICE,
    )
    request_b = _ensure_request(
        booking=booking_b,
        start=base + timedelta(days=1),
        status=MeetingRequestStatus.COMPLETED,
        amount=DEMO_MEETING_PRICE,
        session_id=booking_b.stripe_checkout_session_id,
    )
    RefundRequest.objects.update_or_create(
        meeting_request=request_b,
        defaults={
            "reason": "Demo refund request.",
            "status": RefundStatus.PENDING,
        },
    )

    booking_c = _ensure_booking(
        meeting=approval_meeting,
        seeker=seeker_a,
        status=BookingStatus.PENDING,
        session_id=f"cs_demo_pending_{peer.username}",
        amount=DEMO_MEETING_PRICE,
    )
    _ensure_request(
        booking=booking_c,
        start=base + timedelta(days=2),
        status=MeetingRequestStatus.PENDING_APPROVAL,
        amount=DEMO_MEETING_PRICE,
        session_id=booking_c.stripe_checkout_session_id,
    )
    return 1


def seed_demo_data(
    *,
    email_base: str,
    password: str,
    actor=None,
    include_paused_peer: bool = True,
) -> dict:
    """Create deterministic demo users, content, and local Stripe rows."""
    if not settings.DEMO_DATA_ENABLED:
        msg = "Demo data is disabled."
        raise DemoDataError(msg)
    if not password:
        msg = "A demo account password is required."
        raise DemoDataError(msg)
    local, domain = parse_demo_email_base(email_base)
    requested_base = f"{local}@{domain}"
    validate_test_stripe_keys()

    with transaction.atomic():
        _advisory_lock()
        existing = _demo_users()
        if existing.exists():
            bases = _email_bases(existing)
            if requested_base not in bases:
                raise DemoDataError(
                    "Demo data already exists under a different base email: "
                    + ", ".join(bases)
                    + ". Clean that data up first.",
                )

        home = _home_page()
        _ensure_pages(home)
        country, language, tag = _ensure_taxonomy()

        with override_settings(EMAIL_BACKEND=DEMO_EMAIL_BACKEND):
            peers = []
            pause_index = 2
            for index in range(1, 3):
                username = f"demo-peer-{index:02d}"
                paused = include_paused_peer and index == pause_index
                peers.append(
                    _seed_peer(
                        username=username,
                        email=demo_email(local, domain, username),
                        name=f"Demo Peer {index}",
                        password=password,
                        country=country,
                        language=language,
                        tag=tag,
                        paused=paused,
                    ),
                )
            seekers = [
                _seed_seeker(
                    username=f"demo-seeker-{index:02d}",
                    email=demo_email(local, domain, f"demo-seeker-{index:02d}"),
                    name=f"Demo Seeker {index}",
                    password=password,
                    country=country,
                    language=language,
                )
                for index in range(1, 3)
            ]
            for index, peer in enumerate(peers, start=1):
                _seed_activity(
                    peer=peer,
                    seekers=seekers,
                    language=language,
                    country=country,
                    tag=tag,
                    paused=include_paused_peer and index == pause_index,
                )

    return demo_data_status(email_base=requested_base)


def cleanup_demo_data(*, email_base: str, actor=None, dry_run: bool = False) -> dict:
    """Remove demo data for the supplied base email."""
    if not settings.DEMO_DATA_ENABLED:
        msg = "Demo data is disabled."
        raise DemoDataError(msg)
    local, domain = parse_demo_email_base(email_base)

    with transaction.atomic():
        _advisory_lock()
        users = _demo_users(f"{local}@{domain}")
        meetings = _demo_meetings(users)
        summary = demo_data_status(email_base=f"{local}@{domain}")
        if dry_run or not users.exists():
            return summary

        from djstripe.models import Account as StripeAccount  # noqa: PLC0415
        from djstripe.models import Customer as StripeCustomer  # noqa: PLC0415
        from djstripe.models import Subscription as StripeSubscription  # noqa: PLC0415

        from neuromancers_network.inbox.models import Notification  # noqa: PLC0415
        from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
        from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
        from neuromancers_network.meetings.models import RefundRequest  # noqa: PLC0415
        from neuromancers_network.meetings.models import Review  # noqa: PLC0415
        from neuromancers_network.payments.models import PaymentProfile  # noqa: PLC0415
        from neuromancers_network.peers.models import CalendarEvent  # noqa: PLC0415
        from neuromancers_network.peers.models import PeerAvailability  # noqa: PLC0415
        from neuromancers_network.peers.models import PeerSubscription  # noqa: PLC0415
        from neuromancers_network.taxonomy.models import AllowedTag  # noqa: PLC0415
        from neuromancers_network.taxonomy.models import TagGroup  # noqa: PLC0415

        profiles = list(PaymentProfile.objects.filter(user__in=users))
        subscriptions = list(
            PeerSubscription.objects.filter(payment_profile__in=profiles),
        )
        subscription_ids = [item.subscription_id for item in subscriptions]
        customer_ids = [item.stripe_customer_id_id for item in profiles]
        account_ids = [
            item.stripe_connect_account_id_id
            for item in profiles
            if item.stripe_connect_account_id_id
        ]

        RefundRequest.objects.filter(
            meeting_request__meeting__in=meetings,
        ).delete()
        Review.objects.filter(
            meeting_request__meeting__in=meetings,
        ).delete()
        MeetingRequest.objects.filter(meeting__in=meetings).delete()
        Booking.objects.filter(meeting__in=meetings).delete()
        Notification.objects.filter(recipient__in=users).delete()
        CalendarEvent.objects.filter(owner__in=users).delete()
        PeerAvailability.objects.filter(peer__in=users).delete()
        meetings.delete()
        PeerSubscription.objects.filter(payment_profile__in=profiles).delete()
        PaymentProfile.objects.filter(user__in=users).delete()
        with override_settings(EMAIL_BACKEND=DEMO_EMAIL_BACKEND):
            users.delete()
        StripeSubscription.objects.filter(id__in=subscription_ids).delete()
        StripeAccount.objects.filter(id__in=account_ids).delete()
        StripeCustomer.objects.filter(id__in=customer_ids).delete()

        group = TagGroup.objects.filter(slug=DEMO_TAG_GROUP_SLUG).first()
        if group is not None:
            AllowedTag.objects.filter(group=group).delete()
            group.delete()

    return summary
