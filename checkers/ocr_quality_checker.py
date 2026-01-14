"""OCR quality checker (V7 Gate D)."""

from checkers.base import BaseChecker
from src.schemas.models import Document, Finding, Severity


class OCRQualityChecker(BaseChecker):
    """Checks OCR quality metrics."""

    @property
    def name(self) -> str:
        """Checker name."""
        return "OCRQualityChecker"

    def check(self, document: Document) -> list[Finding]:
        """Check OCR quality."""
        findings: list[Finding] = []

        # Collect pages with bad OCR quality
        bad_pages: list[tuple[int, float]] = []
        
        for page in document.pages:
            # Check if page has ocr_quality attribute (V7)
            if hasattr(page, "ocr_quality") and page.ocr_quality:
                quality = page.ocr_quality
                if isinstance(quality, dict):
                    status = quality.get("status", "unknown")
                    score = quality.get("score", 0.0)
                    
                    if status == "bad":
                        bad_pages.append((page.page_index, score))

        # Report bad pages
        if bad_pages:
            # Sort by score (worst first)
            bad_pages.sort(key=lambda x: x[1])
            top_5 = bad_pages[:5]
            
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=top_5[0][0] if top_5 else 0,
                    reason=f"{len(bad_pages)} pages have bad OCR quality. Top 5 worst: {[(p, round(s, 2)) for p, s in top_5]}",
                    severity=Severity.WARNING,
                )
            )

        # Check for pages with high repeat_run_max (noise)
        high_noise_pages: list[tuple[int, int]] = []
        for page in document.pages:
            if hasattr(page, "ocr_quality") and page.ocr_quality:
                quality = page.ocr_quality
                if isinstance(quality, dict):
                    repeat_run = quality.get("repeat_run_max", 0)
                    if repeat_run >= 10:
                        high_noise_pages.append((page.page_index, repeat_run))

        if high_noise_pages:
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=high_noise_pages[0][0],
                    reason=f"{len(high_noise_pages)} pages have high noise (repeat_run_max >= 10): {high_noise_pages[:5]}",
                    severity=Severity.WARNING,
                )
            )

        return findings
