from datetime import date

from django.utils import timezone

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
