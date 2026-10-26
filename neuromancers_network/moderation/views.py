"""Member-facing download of a ready data export."""

from __future__ import annotations

from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import View

from .export import verify_export_download_token
from .models import AccountDeletionRequest
from .models import DataExportRequest
from .models import DeletionStatus
from .models import ExportStatus
from .services import cancel_account_deletion
from .tokens import read_deletion_cancel_token


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
            message = "You do not have access to this export"
            raise PermissionDenied(message)

        if export.expires_at is not None and export.expires_at < timezone.now():
            raise Http404
        if not export.file:
            raise Http404

        return FileResponse(
            export.file.open("rb"),
            as_attachment=True,
            filename=Path(export.file.name).name,
        )


@method_decorator(never_cache, name="dispatch")
class AccountDeletionCancelView(View):
    """Confirm and cancel a pending account deletion from a signed link."""

    template_name = "moderation/deletion_cancel.html"

    def get(self, request, token):
        deletion = self._pending_deletion(token)
        if deletion is None:
            return self._invalid(request)
        return render(
            request,
            self.template_name,
            {"deletion": deletion, "token": token, "state": "confirm"},
        )

    def post(self, request, token):
        payload = read_deletion_cancel_token(token)
        if payload is None:
            return self._invalid(request)
        with transaction.atomic():
            deletion = (
                AccountDeletionRequest.objects.select_for_update()
                .select_related("user")
                .filter(
                    pk=payload["deletion_id"],
                    user_id=payload["user_id"],
                    status=DeletionStatus.PENDING,
                )
                .first()
            )
            if deletion is None:
                return self._invalid(request)
            cancel_account_deletion(
                deletion.user,
                actor=deletion.user,
                request=request,
            )
        return render(
            request,
            self.template_name,
            {"deletion": deletion, "state": "cancelled"},
        )

    @staticmethod
    def _pending_deletion(token):
        payload = read_deletion_cancel_token(token)
        if payload is None:
            return None
        return (
            AccountDeletionRequest.objects.select_related("user")
            .filter(
                pk=payload["deletion_id"],
                user_id=payload["user_id"],
                status=DeletionStatus.PENDING,
            )
            .first()
        )

    def _invalid(self, request):
        return render(
            request,
            self.template_name,
            {"state": "invalid"},
            status=410,
        )
