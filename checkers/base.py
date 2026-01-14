"""Base checker interface."""

from abc import ABC, abstractmethod

from src.schemas.models import Document, Finding


class BaseChecker(ABC):
    """Base class for all checkers."""

    @abstractmethod
    def check(self, document: Document) -> list[Finding]:
        """Run checks and return findings."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Checker name."""
        pass
