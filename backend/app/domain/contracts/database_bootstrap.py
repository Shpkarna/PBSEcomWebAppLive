"""Contract for database bootstrap / initialization."""
from abc import ABC, abstractmethod


class DatabaseBootstrap(ABC):
    """Storage-agnostic bootstrap interface for database initialization."""

    @abstractmethod
    def bootstrap(self) -> None:
        """Ensure collections, indexes, seed data, and log database exist."""
