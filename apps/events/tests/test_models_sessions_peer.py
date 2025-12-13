from datetime import datetime, timedelta

import pytz
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from guardian.shortcuts import assign_perm
from model_bakery import baker
from wagtail.test.utils import WagtailPageTestCase

from apps.events.models_pages.wagtail_detail_pages import PeerSessionDetailPage
from apps.events.models_pages.wagtail_pages import SessionsIndexPage
from apps.events.models_sessions.peer import PeerSession, PeerSessionRequest, User


class PeerSessionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = baker.make(User, username="host_user", _refresh_after_create=True)
        assign_perm("events.add_peersession", user)
        cls.session = baker.make(
            PeerSession,
            title="Test Session",
            is_published=True,
            host=user,
            _refresh_after_create=True,
        )

    def test_no_session_without_permission(self):
        new_host = baker.make(User, username="new_host", _refresh_after_create=True)
        with self.assertRaises(PeerSession.DoesNotExist):
            baker.make(
                PeerSession,
                title="Unauthorized Session",
                is_published=True,
                host=new_host,
                _refresh_after_create=True,
            )

    def test_unique_title_host_is_published(self):
        session = baker.make(
            PeerSession,
            title="Test Session",
            is_published=False,
            host=self.session.host,
            _refresh_after_create=True,
        )
        self.assertEqual(
            (session.host, session.title), (self.session.host, self.session.title)
        )
        self.assertIsNone(session.validate_constraints())

    def test_non_unique_title_host_is_published(self):
        with self.assertRaises(IntegrityError):
            baker.make(
                PeerSession,
                title="Test Session",
                is_published=True,
                host=self.session.host,
                _refresh_after_create=True,
            )

    def test_no_payment_required_for_free_session(self):
        free_session = baker.make(
            PeerSession,
            title="Free Session",
            is_published=True,
            price=0,
            host=self.session.host,
            _refresh_after_create=True,
        )
        self.assertTrue(free_session.access_before_payment)

        with self.assertRaises(ValidationError):
            free_session.access_before_payment = False
            free_session.validate_constraints()

    def test_no_host_change_on_update(self):
        new_host = baker.make(User, username="new_host", _refresh_after_create=True)
        session = baker.make(
            PeerSession,
            title="Don't change the host!",
            is_published=True,
            price=0,
            host=self.session.host,
            _refresh_after_create=True,
        )

        session.host = new_host

        with self.assertRaises(ValidationError):
            session.save()


class PeerSessionRequestTestCase(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        user = baker.make(User, username="host_user", _refresh_after_create=True)
        assign_perm("events.add_peersession", user)

        session = baker.make(
            PeerSession,
            title="Test Session",
            is_published=True,
            host=user,
            require_request_approval=False,
            _refresh_after_create=True,
        )
        sessions_index_page = SessionsIndexPage.objects.get_or_create(title="Sessions")[
            0
        ]
        sessions_index_page.specific.save_revision().publish()
        detail_page = PeerSessionDetailPage(
            session=session,
            title=session.title,
            slug=f"peer-{session.pk}",
        )
        sessions_index_page.add_child(instance=detail_page)
        detail_page.save_revision().publish()

        attendee = baker.make(User, _refresh_after_create=True)
        assign_perm("request_session", attendee, session)

        cls.session_request = PeerSessionRequest.objects.create(
            starts_at=datetime(2000, 1, 1, 0, 0, tzinfo=pytz.UTC),
            ends_at=datetime(2000, 1, 1, 1, 0, tzinfo=pytz.UTC),
            session=session,
            attendee=attendee,
        )
        cls.session_request.save()

    def test_unique_peer_session_request(self):
        new_request = PeerSessionRequest.objects.create(
            starts_at=self.session_request.starts_at + timedelta(minutes=30),
            ends_at=self.session_request.ends_at + timedelta(minutes=30),
            session=self.session_request.session,
            attendee=self.session_request.attendee,
        )
        new_request.save()
        self.assertIsNone(new_request.validate_constraints())
