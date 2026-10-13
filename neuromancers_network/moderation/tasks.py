from celery import shared_task

from neuromancers_network.moderation.export import build_export_file
from neuromancers_network.moderation.models import DataExportRequest
from neuromancers_network.moderation.services import purge_due_accounts


@shared_task
def purge_due_account_deletions() -> int:
    """Anonymise accounts whose deletion grace period has elapsed."""
    return purge_due_accounts()


@shared_task
def build_data_export(export_id: int) -> None:
    """Render a queued data export to a file."""
    export_request = DataExportRequest.objects.filter(pk=export_id).first()
    if export_request is None:
        return
    build_export_file(export_request)
