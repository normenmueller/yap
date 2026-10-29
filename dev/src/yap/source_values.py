"""Checked scalar values shared by authored-source decoders."""

from datetime import date


def canonical_date(value: object, where: str) -> date:
    """Require a real calendar date written exactly as YYYY-MM-DD."""
    message = f'{where}: expected a date in YYYY-MM-DD format.'
    if not isinstance(value, str):
        raise ValueError(message)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(message) from None
    if parsed.isoformat() != value:
        raise ValueError(message)
    return parsed
