"""Semantic section checker (V7 Gate D)."""

from checkers.base import BaseChecker
from src.schemas.models import Document, Finding, Severity


class SemanticSectionChecker(BaseChecker):
    """Checks that required semantic sections are present."""

    @property
    def name(self) -> str:
        """Checker name."""
        return "SemanticSectionChecker"

    def check(self, document: Document) -> list[Finding]:
        """Check semantic sections."""
        findings: list[Finding] = []

        # Collect semantic sections
        semantic_sections = set()
        for page in document.pages:
            if page.semantic_section:
                semantic_sections.add(page.semantic_section)

        total_pages = len(document.pages)

        # V7: Mini-run requirements (3-5 pages)
        if total_pages <= 5:
            # Require at least cover and toc
            required_sections = {"cover", "toc"}
            missing = required_sections - semantic_sections

            if missing:
                findings.append(
                    Finding(
                        checker=self.name,
                        page_index=0,
                        reason=f"Mini-run missing required sections: {missing}. Found: {semantic_sections}",
                        severity=Severity.WARNING,
                    )
                )
        else:
            # Full-run requirements
            required_sections = {"income_statement", "balance_sheet"}
            missing = required_sections - semantic_sections

            if missing:
                findings.append(
                    Finding(
                        checker=self.name,
                        page_index=0,
                        reason=f"Full-run missing required sections: {missing}. Found: {semantic_sections}",
                        severity=Severity.WARNING,
                    )
                )

        # Check that semantic_section is not null for all pages
        pages_without_section = [
            i for i, page in enumerate(document.pages) if not page.semantic_section
        ]
        if pages_without_section:
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=pages_without_section[0],
                    reason=f"{len(pages_without_section)} pages have null semantic_section: {pages_without_section[:10]}",
                    severity=Severity.INFO,
                )
            )

        return findings
