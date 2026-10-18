"""Data export: ZIP contents, cooldown, download auth and sweep."""

from __future__ import annotations

import io
import zipfile
from datetime import timedelta
from http import HTTPStatus

import pytest
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils import timezone

from neuromancers_network.moderation.export import MAX_EXPORT_ATTEMPTS
from neuromancers_network.moderation.export import build_export_file
from neuromancers_network.moderation.export import export_download_token
from neuromancers_network.moderation.export import request_data_export
from neuromancers_network.moderation.export import sweep_data_exports
from neuromancers_network.moderation.models import DataExportRequest
from neuromancers_network.moderation.models import ExportStatus
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def export_storage(tmp_path):
    """Point the export field's storage at a temp dir (it is fixed at import)."""
    field = DataExportRequest._meta.get_field("file")  # noqa: SLF001
    original = field.storage
    field.storage = FileSystemStorage(location=str(tmp_path))
    yield tmp_path
    field.storage = original


@pytest.fixture
def _no_celery(monkeypatch):
    class _Dummy:
        def delay(self, pk):
            return None

    monkeypatch.setattr(
        "neuromancers_network.moderation.tasks.build_data_export",
        _Dummy(),
    )


class TestBuildExport:
    def test_writes_zip_of_csvs_and_marks_ready(self, export_storage):
        user = UserFactory()
        export = DataExportRequest.objects.create(user=user)

        build_export_file(export)

        export.refresh_from_db()
        assert export.status == ExportStatus.READY
        assert export.file.name.endswith(".zip")
        assert export.expires_at is not None
        with zipfile.ZipFile(io.BytesIO(export.file.read())) as archive:
            names = set(archive.namelist())
        assert {"account.csv", "meetings.csv", "notifications.csv"} <= names


@pytest.mark.usefixtures("_no_celery")
class TestRequestExport:
    def test_blocks_when_in_progress(self):
        user = UserFactory()
        DataExportRequest.objects.create(user=user, status=ExportStatus.PENDING)

        with pytest.raises(ValueError, match="in progress"):
            request_data_export(user)

    def test_blocks_within_cooldown(self):
        user = UserFactory()
        DataExportRequest.objects.create(
            user=user,
            status=ExportStatus.READY,
            completed_at=timezone.now(),
        )

        with pytest.raises(ValueError, match="later"):
            request_data_export(user)

    def test_creates_and_queues(self):
        user = UserFactory()

        export = request_data_export(user)

        assert export.status == ExportStatus.PENDING


class TestSweep:
    def _stale_export(self, *, attempts):
        export = DataExportRequest.objects.create(
            user=UserFactory(),
            status=ExportStatus.PROCESSING,
            attempts=attempts,
        )
        DataExportRequest.objects.filter(pk=export.pk).update(
            updated_at=timezone.now() - timedelta(hours=2),
        )
        return export

    def test_retries_increment_attempts(self, monkeypatch):
        export = self._stale_export(attempts=0)
        retried = []
        monkeypatch.setattr(
            "neuromancers_network.moderation.export.build_export_file",
            lambda export_request: retried.append(export_request.pk),
        )

        sweep_data_exports()

        export.refresh_from_db()
        assert export.attempts == 1
        assert retried == [export.pk]

    def test_stops_after_max_attempts(self, monkeypatch):
        export = self._stale_export(attempts=MAX_EXPORT_ATTEMPTS)
        monkeypatch.setattr(
            "neuromancers_network.moderation.export.build_export_file",
            lambda export_request: pytest.fail("should not retry"),
        )

        sweep_data_exports()

        export.refresh_from_db()
        assert export.status == ExportStatus.FAILED
        assert export.error == "Exceeded retry limit"

    def test_purges_expired(self, export_storage):
        user = UserFactory()
        export = DataExportRequest.objects.create(
            user=user,
            status=ExportStatus.READY,
            expires_at=timezone.now() - timedelta(hours=1),
        )

        purged = sweep_data_exports()

        assert purged == 1
        assert not DataExportRequest.objects.filter(pk=export.pk).exists()


class TestDownload:
    def _ready_export(self, owner):
        export = DataExportRequest.objects.create(user=owner)
        build_export_file(export)
        return export

    def test_bad_token_is_404(self, client, export_storage):
        owner = UserFactory()
        export = self._ready_export(owner)

        response = client.get(
            reverse("data_export_download", args=[export.pk, "bogus"]),
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_anonymous_is_forbidden(self, client, export_storage):
        owner = UserFactory()
        export = self._ready_export(owner)
        token = export_download_token(export)

        response = client.get(reverse("data_export_download", args=[export.pk, token]))

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_non_owner_is_forbidden(self, client, export_storage):
        owner = UserFactory()
        export = self._ready_export(owner)
        token = export_download_token(export)
        client.force_login(UserFactory())

        response = client.get(reverse("data_export_download", args=[export.pk, token]))

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_owner_can_download(self, client, export_storage):
        owner = UserFactory()
        export = self._ready_export(owner)
        token = export_download_token(export)
        client.force_login(owner)

        response = client.get(reverse("data_export_download", args=[export.pk, token]))

        assert response.status_code == HTTPStatus.OK
        assert response["Content-Disposition"].endswith('.zip"')
