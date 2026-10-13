import json

import pytest

from neuromancers_network.moderation.export import build_export_file
from neuromancers_network.moderation.export import collect_user_data
from neuromancers_network.moderation.export import request_data_export
from neuromancers_network.moderation.models import DataExportRequest
from neuromancers_network.moderation.models import ExportStatus
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestCollectUserData:
    def test_includes_account_and_empty_collections(self):
        user = UserFactory()

        data = collect_user_data(user)

        assert data["account"]["id"] == user.pk
        assert data["meetings"] == []
        assert "notifications" in data


class TestBuildExport:
    def test_writes_file_and_marks_ready(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        user = UserFactory()
        export = DataExportRequest.objects.create(user=user)

        build_export_file(export)

        export.refresh_from_db()
        assert export.status == ExportStatus.READY
        assert export.file.name.endswith(".json")
        content = json.loads(export.file.read().decode())
        assert content["account"]["id"] == user.pk


class TestRequestExport:
    def test_creates_and_queues(self, monkeypatch):
        called = {}

        class _Dummy:
            def delay(self, pk):
                called["pk"] = pk

        monkeypatch.setattr(
            "neuromancers_network.moderation.tasks.build_data_export",
            _Dummy(),
        )
        user = UserFactory()

        export = request_data_export(user)

        assert export.status == ExportStatus.PENDING
        assert called["pk"] == export.pk
