"""HTTP and transport adapters; no domain logic belongs here."""

from .app import create_app

__all__ = ["create_app"]
