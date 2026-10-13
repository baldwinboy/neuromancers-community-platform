import pytest
from django.test import RequestFactory

from neuromancers_network.core.audit import client_ip
from neuromancers_network.core.audit import record_audit
from neuromancers_network.core.models import AccountAuditLog
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestClientIp:
    def test_none_request(self):
        assert client_ip(None) is None

    def test_remote_addr_fallback(self):
        request = RequestFactory().get("/")
        request.META["REMOTE_ADDR"] = "203.0.113.5"

        assert client_ip(request) == "203.0.113.5"


class TestRecordAudit:
    def test_records_actor_subject_and_metadata(self):
        actor = UserFactory()
        subject = UserFactory()
        request = RequestFactory().post("/")
        request.META["REMOTE_ADDR"] = "203.0.113.5"
        request.META["HTTP_USER_AGENT"] = "pytest-agent"

        log = record_audit(
            action="account.deactivate",
            actor=actor,
            user=subject,
            request=request,
            event_type="account_deactivated",
            changes={"is_active": [True, False]},
            reason="requested",
        )

        assert log.actor == actor
        assert log.user == subject
        assert log.action == "account.deactivate"
        assert log.event_type == "account_deactivated"
        assert log.ip_address == "203.0.113.5"
        assert log.user_agent == "pytest-agent"
        assert log.changes == {"is_active": [True, False]}
        assert log.reason == "requested"

    def test_anonymous_actor_is_ignored(self):
        log = record_audit(action="system.tick", actor=None)

        assert log.actor is None
        assert log.user is None
        assert log.ip_address is None

    def test_update_is_blocked(self):
        log = record_audit(action="account.deactivate")
        log.reason = "changed"

        with pytest.raises(ValueError, match="append-only"):
            log.save()

        assert AccountAuditLog.objects.get(pk=log.pk).reason == ""

    def test_delete_is_blocked(self):
        log = record_audit(action="account.deactivate")

        with pytest.raises(ValueError, match="cannot be deleted"):
            log.delete()

        assert AccountAuditLog.objects.filter(pk=log.pk).exists()
