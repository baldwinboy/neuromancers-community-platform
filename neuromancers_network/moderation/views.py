"""Member-facing download of a ready data export."""

from __future__ import annotations

from pathlib import Path

from django.contrib.auth.views import redirect_to_login
from django.http import FileResponse
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import View

from .export import verify_export_download_token
from .models import DataExportRequest
from .models import ExportStatus


class DataExportDownloadView(View):
    """Stream a ready export to its owner (or staff) via a signed link."""

    def get(self, request, pk, token):
        if not verify_export_download_token(pk, token):
            raise Http404
        export = get_object_or_404(
            DataExportRequest,
            pk=pk,
            status=ExportStatus.READY,
        )

        user = request.user
        is_owner = (
            getattr(user, "is_authenticated", False) and user.pk == export.user_id
        )
        if not (is_owner or getattr(user, "is_staff", False)):
            return redirect_to_login(request.get_full_path())

        if export.expires_at is not None and export.expires_at < timezone.now():
            raise Http404
        if not export.file:
            raise Http404

        return FileResponse(
            export.file.open("rb"),
            as_attachment=True,
            filename=Path(export.file.name).name,
        )
