import uuid
from datetime import datetime, timedelta

import pytz
from django.core.exceptions import ValidationError
from django.test import TestCase
from model_bakery import baker

from apps.events.models_sessions.group import GroupSession
from apps.events.models_sessions.peer import PeerSession, PeerSessionRequest, User


class PeerSessionRequestTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        session = baker.make(PeerSession)
        starts_at = datetime(2000, 1, 1, 0, 0, tzinfo=pytz.UTC)
        ends_at = starts_at + timedelta(hours=1)
        attendee = baker.make(User)
        cls.peer_session_request = PeerSessionRequest.objects.create(
            starts_at=starts_at,
            ends_at=ends_at,
            session=session,
            attendee=attendee,
            status=0,
        )

    def test_unique_peer_session_request(self):
        starts_at = self.peer_session_request.starts_at + timedelta(hours=1)
        ends_at = starts_at + timedelta(hours=1)
        request_attributes = {
            field: getattr(self.peer_session_request, field)
            for field in [
                field.name for field in self.peer_session_request._meta.fields
            ]
        }
        request_attributes.update(
            {"starts_at": starts_at, "ends_at": ends_at, "id": uuid.uuid4()}
        )

        new_request = PeerSessionRequest(**request_attributes)

        new_request.validate_unique()

    def test_non_unique_peer_session_request(self):
        starts_at = self.peer_session_request.starts_at + timedelta(minutes=30)
        request_attributes = {
            field: getattr(self.peer_session_request, field)
            for field in [
                field.name for field in self.peer_session_request._meta.fields
            ]
        }
        request_attributes.update({"starts_at": starts_at, "id": uuid.uuid4()})

        new_request = PeerSessionRequest(**request_attributes)

        with self.assertRaises(ValidationError):
            new_request.validate_unique()


class GroupSessionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        starts_at = datetime(2000, 1, 1, 0, 0, tzinfo=pytz.UTC)
        ends_at = starts_at + timedelta(hours=1)
        host = baker.make(User)
        cls.group_session = baker.make(
            GroupSession,
            starts_at=starts_at,
            ends_at=ends_at,
            host=host,
            is_published=True,
        )

    def test_unique_group_session(self):
        starts_at = self.group_session.starts_at + timedelta(hours=1)
        ends_at = starts_at + timedelta(hours=1)
        session_attributes = {
            field: getattr(self.group_session, field)
            for field in [field.name for field in self.group_session._meta.fields]
        }
        session_attributes.update(
            {
                "is_published": False,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "id": uuid.uuid4(),
            }
        )

        new_session = GroupSession(**session_attributes)

        new_session.validate_unique()

    def test_non_unique_group_session(self):
        starts_at = self.group_session.starts_at + timedelta(minutes=30)
        session_attributes = {
            field: getattr(self.group_session, field)
            for field in [field.name for field in self.group_session._meta.fields]
        }
        session_attributes.update(
            {"is_published": False, "starts_at": starts_at, "id": uuid.uuid4()}
        )

        new_session = GroupSession(**session_attributes)

        with self.assertRaises(ValidationError):
            new_session.validate_unique()
