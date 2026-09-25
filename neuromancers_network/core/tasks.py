from celery import shared_task
from django.core.management import call_command


@shared_task
def update_search_index():
    """Rebuild the Wagtail search index."""
    call_command("update_index")
