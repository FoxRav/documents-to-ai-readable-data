"""Schema validation checker."""

from checkers.base import BaseChecker
from src.schemas.models import Document, Finding, Severity


class SchemaChecker(BaseChecker):
    """Validates document against JSON schema."""

    @property
    def name(self) -> str:
        """Checker name."""
        return "SchemaChecker"

    def check(self, document: Document) -> list[Finding]:
        """Validate document schema."""
        findings: list[Finding] = []

        try:
            # Pydantic validation happens on model creation
            # This checker verifies the document structure is complete
            if not document.pdf:
                findings.append(
                    Finding(
                        checker=self.name,
                        page_index=0,
                        reason="Missing PDF metadata",
                        severity=Severity.ERROR,
                    )
                )

            if not document.pages:
                findings.append(
                    Finding(
                        checker=self.name,
                        page_index=0,
                        reason="No pages in document",
                        severity=Severity.ERROR,
                    )
                )

            # Check each page has required fields
            for page in document.pages:
                if page.width <= 0 or page.height <= 0:
                    findings.append(
                        Finding(
                            checker=self.name,
                            page_index=page.page_index,
                            reason=f"Invalid page dimensions: {page.width}x{page.height}",
                            severity=Severity.ERROR,
                        )
                    )

        except Exception as e:
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=0,
                    reason=f"Schema validation error: {e}",
                    severity=Severity.ERROR,
                )
            )

        return findings
