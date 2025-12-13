from datetime import datetime

import pytz
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from guardian.shortcuts import assign_perm
from model_bakery import baker

from apps.events.models_sessions.group import GroupSession, User


class GroupSessionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = baker.make(User, username="host_user", _refresh_after_create=True)
        assign_perm("events.add_groupsession", user)
        cls.session = baker.make(
            GroupSession,
            starts_at=datetime(2000, 1, 1, 0, 0, tzinfo=pytz.UTC),
            ends_at=datetime(2000, 1, 1, 1, 0, tzinfo=pytz.UTC),
            title="Test Session",
            is_published=True,
            host=user,
            _refresh_after_create=True,
        )

    def test_no_session_without_permission(self):
        new_host = baker.make(User, username="new_host", _refresh_after_create=True)
        with self.assertRaises(GroupSession.DoesNotExist):
            baker.make(
                GroupSession,
                starts_at=datetime(2000, 1, 1, 0, 0, tzinfo=pytz.UTC),
                ends_at=datetime(2000, 1, 1, 1, 0, tzinfo=pytz.UTC),
                title="Unauthorized Session",
                is_published=True,
                host=new_host,
                _refresh_after_create=True,
            )

    def test_unique_title_host_is_published(self):
        session = baker.make(
            GroupSession,
            starts_at=datetime(2000, 1, 2, 0, 0, tzinfo=pytz.UTC),
            ends_at=datetime(2000, 1, 2, 1, 0, tzinfo=pytz.UTC),
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
                GroupSession,
                starts_at=datetime(2000, 1, 3, 0, 0, tzinfo=pytz.UTC),
                ends_at=datetime(2000, 1, 3, 1, 0, tzinfo=pytz.UTC),
                title="Test Session",
                is_published=True,
                host=self.session.host,
                _refresh_after_create=True,
            )

    def test_no_payment_required_for_free_session(self):
        free_session = baker.make(
            GroupSession,
            starts_at=datetime(2000, 1, 4, 0, 0, tzinfo=pytz.UTC),
            ends_at=datetime(2000, 1, 4, 1, 0, tzinfo=pytz.UTC),
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

    def test_no_ends_at_before_starts_at(self):
        with self.assertRaises(IntegrityError):
            baker.make(
                GroupSession,
                starts_at=datetime(2000, 1, 4, 1, 0, tzinfo=pytz.UTC),
                ends_at=datetime(2000, 1, 4, 0, 0, tzinfo=pytz.UTC),
                title="Invalid Session",
                is_published=True,
                price=0,
                host=self.session.host,
                _refresh_after_create=True,
            )

    def test_no_host_change_on_update(self):
        new_host = baker.make(User, username="new_host", _refresh_after_create=True)
        session = baker.make(
            GroupSession,
            starts_at=datetime(2000, 1, 4, 0, 0, tzinfo=pytz.UTC),
            ends_at=datetime(2000, 1, 4, 1, 0, tzinfo=pytz.UTC),
            title="Don't change the host!",
            is_published=True,
            price=0,
            host=self.session.host,
            _refresh_after_create=True,
        )

        session.host = new_host

        with self.assertRaises(ValidationError):
            session.save()
