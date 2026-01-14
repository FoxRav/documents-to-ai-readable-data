"""Sum consistency checker."""

import re

from checkers.base import BaseChecker
from src.schemas.models import Document, Finding, Severity, SumCheck, Table


class SumChecker(BaseChecker):
    """Checks sum consistency in tables."""

    @property
    def name(self) -> str:
        """Checker name."""
        return "SumChecker"

    def parse_number(self, text: str) -> float | None:
        """Parse number from text (handles thousand separators, decimals, etc.)."""
        if not text or not text.strip():
            return None

        # Remove common formatting
        text = text.strip().replace(" ", "").replace(",", ".").replace("€", "").replace("%", "")

        # Handle parentheses as negative
        is_negative = text.startswith("(") and text.endswith(")")
        if is_negative:
            text = text[1:-1]

        # Extract number
        match = re.search(r"-?\d+\.?\d*", text)
        if match:
            try:
                value = float(match.group())
                return -value if is_negative else value
            except ValueError:
                pass

        return None

    def check(self, document: Document) -> list[Finding]:
        """Check sum consistency."""
        findings: list[Finding] = []

        for page in document.pages:
            for item in page.items:
                if not isinstance(item, Table):
                    continue

                # This is a Table
                table = item
                if not table.cells:
                    continue

                # Find sum rows (heuristic: rows with "YHTEENSÄ", "TOTAL", etc.)
                sum_keywords = ["yhteensä", "total", "sum", "kokonaismäärä"]

                # Group cells by row
                rows: dict[int, list] = {}
                for cell in table.cells:
                    if cell.row not in rows:
                        rows[cell.row] = []
                    rows[cell.row].append(cell)

                # Check each row
                for row_idx, row_cells in rows.items():
                    # Check if this is a sum row
                    first_cell_text = row_cells[0].text_raw.lower() if row_cells else ""
                    is_sum_row = any(keyword in first_cell_text for keyword in sum_keywords)

                    if is_sum_row:
                        # Try to find expected sum from other cells in row
                        numeric_values = []
                        for cell in row_cells[1:]:  # Skip first (label)
                            value = self.parse_number(cell.text_raw)
                            if value is not None:
                                numeric_values.append(value)

                        if len(numeric_values) >= 2:
                            # Compare values (simple heuristic: last value should equal sum of others)
                            expected = sum(numeric_values[:-1])
                            actual = numeric_values[-1]
                            difference = abs(expected - actual)

                            # Allow small rounding differences
                            if difference > 0.01:
                                findings.append(
                                    Finding(
                                        checker=self.name,
                                        page_index=page.page_index,
                                        table_id=table.table_id,
                                        reason=f"Sum mismatch in row {row_idx}: expected {expected}, got {actual}",
                                        severity=Severity.WARNING,
                                    )
                                )

        return findings
