from datetime import datetime


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
