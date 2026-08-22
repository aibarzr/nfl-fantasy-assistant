"""Visible failures for offline data quality gates."""


class DataValidationError(ValueError):
    """A source or curated dataset does not meet its declared contract."""


class PublicationError(RuntimeError):
    """A dataset version cannot be safely staged or promoted."""
