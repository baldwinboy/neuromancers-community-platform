from celery import shared_task

from neuromancers_network.moderation.services import purge_due_accounts


@shared_task
def purge_due_account_deletions() -> int:
    """Anonymise accounts whose deletion grace period has elapsed."""
    return purge_due_accounts()
