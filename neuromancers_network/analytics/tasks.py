from celery import shared_task

from neuromancers_network.analytics.services import sync_analytics_ledgers


@shared_task
def sync_analytics_ledgers_task() -> dict[str, int]:
    """Backfill analytics ledgers from local records (idempotent)."""
    return sync_analytics_ledgers()
