from datetime import date

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

current_year = timezone.now().year
current_birth_years = range(1900, current_year + 1)


def calculate_age(date_of_birth: date):
    """
    Calculate age based on date of birth
    """
    today = timezone.now().date()
    age = int(
        today.year
        - (date_of_birth.year)
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )

    return age


def get_countries() -> dict[str, str]:
    return {k: _(v) for k, v in settings.COUNTRIES}


def get_country_display(iso: str) -> str | None:
    all_counties = get_countries()
    return all_counties.get(iso)
