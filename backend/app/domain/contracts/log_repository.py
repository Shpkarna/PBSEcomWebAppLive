"""Repository contract for audit log persistence operations."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class LogRepository(ABC):
    """Storage-agnostic gateway for audit log operations."""

    @abstractmethod
    def insert_event(self, event: dict) -> None:
        """Persist an immutable audit log event."""

    @abstractmethod
    def list_events(self, limit: int = 100) -> list[dict]:
        """Return recent audit log events, newest first."""
