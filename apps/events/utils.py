import random
from datetime import datetime

from django.conf import settings
from django.utils.translation import gettext as _

from apps.accounts.models_users.user import User


def subtract_event(a: tuple[datetime, datetime], b: tuple[datetime, datetime]):
    """
    Gte non-overlapping times
    """
    results = []
    (a_start, a_end) = a
    (b_start, b_end) = b

    # No overlap at all
    if a_end <= b_start or a_start >= b_end:
        results.append((a_start, a_end))

    # y fully inside x
    elif b_start > a_start and b_end < a_end:
        results.append((a_start, b_start))
        results.append((b_end, a_end))

    # y overlaps start of x
    elif b_start <= a_start and b_end < a_end and b_end > a_start:
        results.append((b_end, a_end))

    # y overlaps end of x
    elif b_start > a_start and b_start < a_end and b_end >= a_end:
        results.append((a_start, b_start))

    # y fully covers x
    # (no need to add anything if y covers x completely)

    return results


def get_languages() -> dict[str, str]:
    return {k: _(v) for k, v in settings.LANGUAGES}


def get_language_display(iso: str) -> str | None:
    all_languages = get_languages()
    return all_languages.get(iso)


def stable_price():
    return random.choice([0, 500, 1000, 1500])  # repeatable small set


def stable_langs():
    return random.choice(["en", "en,fr", "en,es"])


def stable_durations():
    return random.choice(["30,60", "20,40,60"])


def get_host_user():
    return User.objects.filter(groups__name="Peer").order_by("?").first()
