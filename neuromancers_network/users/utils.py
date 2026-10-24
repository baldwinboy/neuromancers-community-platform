def normalize_username(value: str | None) -> str:
    return (value or "").strip().lower()


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()
