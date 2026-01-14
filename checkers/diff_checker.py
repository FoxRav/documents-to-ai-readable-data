"""Diff/regression checker (V8 Gate D)."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from checkers.base import BaseChecker
from src.schemas.models import DiffCheck, Document, Finding, Severity

logger = logging.getLogger(__name__)


class DiffChecker(BaseChecker):
    """
    Compares current document extraction with golden/previous output for regression testing.
    
    Checks:
    - Item count per page
    - Financial type distribution
    - OCR quality summary
    """

    def __init__(self, golden_path: Optional[Path] = None) -> None:
        """
        Initialize diff checker.
        
        Args:
            golden_path: Path to golden document.json for comparison
        """
        self.golden_path = golden_path or Path("out/golden/document.json")

    @property
    def name(self) -> str:
        """Checker name."""
        return "DiffChecker"

    def load_golden(self) -> Optional[dict[str, Any]]:
        """Load golden document for comparison."""
        if not self.golden_path.exists():
            logger.info(f"No golden file at {self.golden_path} - diff check skipped")
            return None
        
        try:
            with open(self.golden_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load golden file: {e}")
            return None

    def count_items_per_page(self, doc_dict: dict[str, Any]) -> dict[int, int]:
        """Count items per page."""
        counts: dict[int, int] = {}
        for page in doc_dict.get("pages", []):
            page_idx = page.get("page_index", 0)
            counts[page_idx] = len(page.get("items", []))
        return counts

    def count_financial_types(self, doc_dict: dict[str, Any]) -> dict[str, int]:
        """Count financial types across document."""
        counts: dict[str, int] = {}
        for page in doc_dict.get("pages", []):
            for item in page.get("items", []):
                ft = item.get("financial_type")
                if ft:
                    counts[ft] = counts.get(ft, 0) + 1
        return counts

    def summarize_ocr_quality(self, doc_dict: dict[str, Any]) -> dict[str, int]:
        """Summarize OCR quality status counts."""
        counts: dict[str, int] = {}
        for page in doc_dict.get("pages", []):
            quality = page.get("ocr_quality", {})
            status = quality.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def check(self, document: Document) -> list[Finding]:
        """Check document against golden for regression."""
        findings: list[Finding] = []
        
        # Load golden
        golden = self.load_golden()
        
        if golden is None:
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=0,
                    reason=f"No golden file found at {self.golden_path} - regression check skipped",
                    severity=Severity.INFO,
                )
            )
            return findings
        
        # Convert current document to dict for comparison
        current = document.model_dump()
        
        # Compare item counts
        current_counts = self.count_items_per_page(current)
        golden_counts = self.count_items_per_page(golden)
        
        item_diffs: list[tuple[int, int, int]] = []  # (page, current, golden)
        for page_idx in set(current_counts.keys()) | set(golden_counts.keys()):
            curr = current_counts.get(page_idx, 0)
            gold = golden_counts.get(page_idx, 0)
            if curr != gold:
                item_diffs.append((page_idx, curr, gold))
        
        if item_diffs:
            diff_summary = ", ".join([f"p{p}:{c}→{g}" for p, c, g in item_diffs[:5]])
            if len(item_diffs) > 5:
                diff_summary += f" (+{len(item_diffs) - 5} more)"
            
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=item_diffs[0][0],
                    reason=f"Item count changed on {len(item_diffs)} pages: {diff_summary}",
                    severity=Severity.WARNING,
                )
            )
        
        # Compare financial types
        current_ft = self.count_financial_types(current)
        golden_ft = self.count_financial_types(golden)
        
        if current_ft != golden_ft:
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=0,
                    reason=(
                        f"Financial type distribution changed. "
                        f"Current: {current_ft}, Golden: {golden_ft}"
                    ),
                    severity=Severity.WARNING,
                )
            )
        
        # Compare OCR quality summary
        current_ocr = self.summarize_ocr_quality(current)
        golden_ocr = self.summarize_ocr_quality(golden)
        
        if current_ocr != golden_ocr:
            findings.append(
                Finding(
                    checker=self.name,
                    page_index=0,
                    reason=(
                        f"OCR quality distribution changed. "
                        f"Current: {current_ocr}, Golden: {golden_ocr}"
                    ),
                    severity=Severity.INFO,
                )
            )
        
        # Summary finding
        total_pages = len(current.get("pages", []))
        golden_pages = len(golden.get("pages", []))
        
        findings.append(
            Finding(
                checker=self.name,
                page_index=0,
                reason=(
                    f"Diff check completed: {total_pages} pages (golden: {golden_pages}), "
                    f"{len(item_diffs)} page(s) with item count changes"
                ),
                severity=Severity.INFO,
            )
        )
        
        return findings


def save_golden(document: Document, output_path: Path) -> None:
    """
    Save current document as golden for future regression tests.
    
    Args:
        document: Document to save as golden
        output_path: Path to save golden file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(document.model_dump_json(indent=2))
    
    logger.info(f"Saved golden document to {output_path}")
