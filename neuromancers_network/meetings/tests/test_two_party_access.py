from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models.pages import BookingDetailPage
from neuromancers_network.core.models.pages import RefundRequestDetailPage
from neuromancers_network.core.wagtail_hooks import hide_inaccessible_detail_pages
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import RefundRequest
from neuromancers_network.meetings.selectors import booking_for_viewer
from neuromancers_network.meetings.selectors import host_bookings
from neuromancers_network.meetings.selectors import meeting_requests_for_context
from neuromancers_network.meetings.selectors import refund_for_viewer
from neuromancers_network.meetings.selectors import user_refunds
from neuromancers_network.meetings.selectors import user_requests
from neuromancers_network.meetings.selectors import viewable_bookings
from neuromancers_network.meetings.selectors import viewable_refunds
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.moderation.visibility import viewer_can_view_source
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

NOT_FOUND = 404


def _home() -> HomePage:
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)
    return home


def _request(user):
    request = RequestFactory().get("/")
    request.user = user or AnonymousUser()
    return request


def _booking():
    peer = make_peer()
    seeker = UserFactory()
    meeting = create_meeting(peer=peer)
    booking = create_booking(
        meeting=meeting,
        seeker=seeker,
        sessions=[{"requested_duration_minutes": 30}],
    )
    return booking, peer, seeker


def _refund(booking):
    return RefundRequest.objects.create(
        meeting_request=booking.sessions.first(),
        reason="Not happy",
    )


class TestBookingSelectors:
    def test_seeker_and_host_see_the_booking(self):
        booking, peer, seeker = _booking()

        assert list(viewable_bookings(_request(seeker))) == [booking]
        assert list(viewable_bookings(_request(peer))) == [booking]
        assert list(host_bookings(_request(peer))) == [booking]
        assert booking_for_viewer(_request(seeker), booking.pk) == booking

    def test_stranger_and_anonymous_see_nothing(self):
        booking, _peer, _seeker = _booking()

        assert not viewable_bookings(_request(UserFactory())).exists()
        assert not viewable_bookings(_request(AnonymousUser())).exists()
        assert booking_for_viewer(_request(UserFactory()), booking.pk) is None

    def test_status_filter(self):
        _booking_row, _peer, seeker = _booking()

        assert not viewable_bookings(
            _request(seeker),
            status=BookingStatus.CANCELLED,
        ).exists()
        assert viewable_bookings(
            _request(seeker),
            status=BookingStatus.PENDING,
        ).exists()

    def test_requests_are_scoped_to_seeker_and_host(self):
        booking, peer, seeker = _booking()
        request_row = booking.sessions.first()

        assert request_row in user_requests(_request(seeker))
        assert request_row in meeting_requests_for_context(_request(peer))
        assert request_row not in meeting_requests_for_context(_request(UserFactory()))


class TestRefundSelectors:
    def test_seeker_and_host_see_the_refund(self):
        booking, peer, seeker = _booking()
        refund = _refund(booking)

        assert list(viewable_refunds(_request(seeker))) == [refund]
        assert list(viewable_refunds(_request(peer))) == [refund]
        assert list(user_refunds(_request(seeker))) == [refund]
        assert refund_for_viewer(_request(peer), refund.pk) == refund

    def test_stranger_sees_nothing(self):
        booking, _peer, _seeker = _booking()
        refund = _refund(booking)

        assert not viewable_refunds(_request(UserFactory())).exists()
        assert refund_for_viewer(_request(UserFactory()), refund.pk) is None


class TestTwoPartyVisibility:
    def test_booking_participants_and_moderators_only(self):
        booking, peer, seeker = _booking()
        moderator = UserFactory(is_staff=True)

        assert viewer_can_view_source(booking, seeker)
        assert viewer_can_view_source(booking, peer)
        assert viewer_can_view_source(booking, moderator)
        assert not viewer_can_view_source(booking, UserFactory())
        assert not viewer_can_view_source(booking, AnonymousUser())

    def test_refund_participants_and_moderators_only(self):
        booking, peer, seeker = _booking()
        refund = _refund(booking)

        assert viewer_can_view_source(refund, seeker)
        assert viewer_can_view_source(refund, peer)
        assert not viewer_can_view_source(refund, UserFactory())
        assert not viewer_can_view_source(refund, AnonymousUser())


class TestTwoPartyDetailPages:
    def test_booking_page_is_participant_scoped(self):
        _home()
        booking, peer, seeker = _booking()
        page = BookingDetailPage.objects.get(source_object_id=booking.pk).specific

        assert hide_inaccessible_detail_pages(page, _request(seeker), (), {}) is None
        assert hide_inaccessible_detail_pages(page, _request(peer), (), {}) is None
        denied = hide_inaccessible_detail_pages(
            page,
            _request(UserFactory()),
            (),
            {},
        )
        assert denied.status_code == NOT_FOUND

    def test_refund_page_is_participant_scoped(self):
        _home()
        booking, _peer, seeker = _booking()
        refund = _refund(booking)
        page = RefundRequestDetailPage.objects.get(
            source_object_id=refund.pk,
        ).specific

        assert hide_inaccessible_detail_pages(page, _request(seeker), (), {}) is None
        denied = hide_inaccessible_detail_pages(
            page,
            _request(UserFactory()),
            (),
            {},
        )
        assert denied.status_code == NOT_FOUND


class TestModelFeedPageScope:
    def test_hidden_page_input_is_emitted_for_model_feeds(self):
        home = _home()
        request = _request(UserFactory())
        html = render_to_string(
            "wagtail_daisIE/blocks/data/feed.html",
            {
                "value": {"feed": {"context_model": "booking", "empty_message": ""}},
                "audience_allowed": True,
                "block": {"id": "test"},
                "block_css": "",
                "block_style": "",
                "host_page": home,
                "feed_url": "/feed/",
                "filters": [],
                "allow_layout_toggle": True,
                "toggle_options": [{"value": "list", "label": "List"}],
                "request": request,
                "items_html": "",
                "total": 0,
                "has_more": False,
                "layout": "list",
                "layout_container_css": "",
                "submit_css": "",
            },
            request=request,
        )

        assert f'name="page" value="{home.pk}"' in html
