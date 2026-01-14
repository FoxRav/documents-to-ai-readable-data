"""Step 60: Normalize data and run QA checks."""

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.schemas.models import (
    BalanceCheck,
    Cell,
    Document,
    Finding,
    QAReport,
    Severity,
    SumCheck,
    Table,
    TableCellExactness,
)

logger = logging.getLogger(__name__)


def normalize_number(text: str) -> tuple[float | None, str | None]:
    """Normalize number: remove thousand separators, handle decimals, units."""
    if not text or not text.strip():
        return None, None

    # Remove spaces, handle thousand separators
    text = text.strip().replace(" ", "").replace(",", ".")

    # Extract unit
    unit = None
    if "€" in text:
        unit = "€"
        text = text.replace("€", "")
    elif "t€" in text:
        unit = "t€"
        text = text.replace("t€", "")
    elif "%" in text:
        unit = "%"
        text = text.replace("%", "")

    # Handle parentheses as negative
    is_negative = text.startswith("(") and text.endswith(")")
    if is_negative:
        text = text[1:-1]

    # Extract number
    match = re.search(r"-?\d+\.?\d*", text)
    if match:
        try:
            value = float(match.group())
            return (-value if is_negative else value, unit)
        except ValueError:
            pass

    return None, None


def normalize_text(text: str) -> str:
    """Normalize text: clean line breaks, hyphens, multiple spaces."""
    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Handle soft hyphens
    text = text.replace("\u00ad", "")

    # Normalize line breaks (keep single newlines, remove multiple)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def normalize_document(document: Document) -> Document:
    """Normalize all text and numbers in document."""
    logger.info("Normalizing document...")

    for page in document.pages:
        for item in page.items:
            if isinstance(item, Table):
                # Table: normalize cells
                table = item
                for cell in table.cells:
                    # Normalize text
                    cell.text_raw = normalize_text(cell.text_raw)

                    # Parse number
                    value_num, unit = normalize_number(cell.text_raw)
                    cell.value_num = value_num
                    cell.unit = unit

            elif hasattr(item, "text"):
                # Block: normalize text
                item.text = normalize_text(item.text)

    logger.info("Normalization completed")
    return document


def run_qa_checks(document: Document) -> QAReport:
    """Run all QA checks."""
    logger.info("Running QA checks...")

    from checkers.schema_checker import SchemaChecker  # noqa: E402
    from checkers.sum_checker import SumChecker  # noqa: E402
    from checkers.semantic_section_checker import SemanticSectionChecker  # noqa: E402
    from checkers.ocr_quality_checker import OCRQualityChecker  # noqa: E402
    from checkers.balance_sheet_checker import BalanceSheetChecker  # noqa: E402  # V8
    from checkers.crossref_checker import CrossRefChecker  # noqa: E402  # V8
    from checkers.diff_checker import DiffChecker  # noqa: E402  # V8

    # Initialize checkers
    checkers = [
        SchemaChecker(),
        SumChecker(),
        SemanticSectionChecker(),  # V7 Gate D
        OCRQualityChecker(),  # V7 Gate D
        BalanceSheetChecker(),  # V8 Gate D
        CrossRefChecker(),  # V8 Gate D
        DiffChecker(),  # V8 Gate D
    ]

    all_findings: list[Finding] = []
    schema_valid = True

    # Run all checkers
    for checker in checkers:
        try:
            findings = checker.check(document)
            all_findings.extend(findings)

            if checker.name == "SchemaChecker" and findings:
                schema_valid = False

        except Exception as e:
            logger.error(f"Error running checker {checker.name}: {e}")
            all_findings.append(
                Finding(
                    checker=checker.name,
                    page_index=0,
                    reason=f"Checker error: {e}",
                    severity=Severity.ERROR,
                )
            )

    # Calculate table cell exactness
    total_cells = 0
    empty_cells = 0
    unparseable_numbers = 0

    for page in document.pages:
        for item in page.items:
            if isinstance(item, Table):
                table = item
                for cell in table.cells:
                    total_cells += 1
                    if not cell.text_raw.strip():
                        empty_cells += 1
                    if cell.value_num is None and cell.text_raw.strip():
                        # Check if it looks like it should be a number
                        if re.search(r"\d", cell.text_raw):
                            unparseable_numbers += 1

    empty_cells_percent = (empty_cells / total_cells * 100) if total_cells > 0 else 0.0
    unparseable_percent = (unparseable_numbers / total_cells * 100) if total_cells > 0 else 0.0

    table_cell_exactness = TableCellExactness(
        empty_cells_percent=empty_cells_percent,
        unparseable_numbers_percent=unparseable_percent,
    )

    # Create QA report
    qa_report = QAReport(
        pdf=document.pdf,
        schema_valid=schema_valid,
        table_cell_exactness=table_cell_exactness,
        sum_checks=[],
        balance_checks=[],
        xref_checks=[],
        diff_checks=[],
        findings=all_findings,
    )

    logger.info(f"QA checks completed: {len(all_findings)} findings")
    return qa_report


def normalize_and_validate(document: Document, output_dir: Path) -> tuple[Document, QAReport]:
    """Normalize document and run QA checks."""
    # V2: Validate document is not empty before processing
    total_items = sum(len(page.items) for page in document.pages)
    if total_items == 0:
        logger.error("❌ V2 VALIDATION FAILED: document.json is empty (no items on any page)")
        logger.error("This indicates Step 41B (OCR text) did not extract data properly")
        logger.error("Pipeline should not proceed to QA with empty document")
        raise ValueError("Document is empty - Step 41B failed to extract data")
    
    logger.info(f"V2 validation passed: {total_items} total items across {len(document.pages)} pages")
    
    normalized = normalize_document(document)
    qa_report = run_qa_checks(normalized)

    # Save normalized document
    doc_path = output_dir / "document.json"
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(normalized.model_dump_json(indent=2))

    # Save QA report
    qa_path = output_dir / "qa_report.json"
    with open(qa_path, "w", encoding="utf-8") as f:
        f.write(qa_report.model_dump_json(indent=2))

    logger.info(f"Normalized document saved to {doc_path}")
    logger.info(f"QA report saved to {qa_path}")

    return normalized, qa_report


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python step_60_normalize_validate.py <document_json_path>")
        sys.exit(1)

    document_path = Path(sys.argv[1])
    output_dir = document_path.parent

    with open(document_path, "r", encoding="utf-8") as f:
        document_dict = json.load(f)

    document = Document.model_validate(document_dict)
    normalize_and_validate(document, output_dir)
