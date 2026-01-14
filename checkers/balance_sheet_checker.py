"""Balance sheet equation checker (V8 Gate D)."""

import re
from typing import Optional

from checkers.base import BaseChecker
from src.schemas.models import (
    BalanceCheck,
    Document,
    Finding,
    FinancialType,
    Severity,
    Table,
)


class BalanceSheetChecker(BaseChecker):
    """
    Checks that balance sheet equation holds: Assets ≈ Liabilities + Equity.
    
    For Finnish municipal reports:
    - "Vastaavaa" (Assets) should equal "Vastattavaa" (Liabilities + Equity)
    """

    @property
    def name(self) -> str:
        """Checker name."""
        return "BalanceSheetChecker"

    def parse_number(self, text: str) -> Optional[float]:
        """Parse number from text (handles Finnish formatting)."""
        if not text or not text.strip():
            return None
        
        # Remove spaces, handle Finnish thousand/decimal separators
        text = text.strip().replace(" ", "").replace(",", ".")
        text = text.replace("€", "").replace("t€", "").replace("%", "")
        
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

    def find_balance_totals(self, table: Table) -> tuple[Optional[float], Optional[float]]:
        """
        Find assets and liabilities totals from balance sheet table.
        
        Returns:
            Tuple of (assets_total, liabilities_total)
        """
        assets_total: Optional[float] = None
        liabilities_total: Optional[float] = None
        
        if not table.cells:
            return None, None
        
        # Keywords for assets (Finnish and English)
        assets_keywords = [
            "vastaavaa yhteensä",
            "vastaavaa yht",
            "total assets",
            "assets total",
            "yhteensä vastaavaa",
        ]
        
        # Keywords for liabilities (Finnish and English)
        liabilities_keywords = [
            "vastattavaa yhteensä",
            "vastattavaa yht",
            "total liabilities",
            "liabilities total",
            "yhteensä vastattavaa",
        ]
        
        # Group cells by row
        rows: dict[int, list] = {}
        for cell in table.cells:
            if cell.row not in rows:
                rows[cell.row] = []
            rows[cell.row].append(cell)
        
        # Check each row for totals
        for row_idx, row_cells in sorted(rows.items()):
            if not row_cells:
                continue
            
            # Get row text (first cell usually has label)
            row_text = row_cells[0].text_raw.lower().strip()
            
            # Get numeric values from rest of row
            numeric_values: list[float] = []
            for cell in row_cells[1:]:
                value = self.parse_number(cell.text_raw)
                if value is not None:
                    numeric_values.append(value)
            
            # Check for assets total
            if any(kw in row_text for kw in assets_keywords):
                if numeric_values:
                    # Take last numeric value (typically the total)
                    assets_total = numeric_values[-1]
            
            # Check for liabilities total
            if any(kw in row_text for kw in liabilities_keywords):
                if numeric_values:
                    liabilities_total = numeric_values[-1]
        
        return assets_total, liabilities_total

    def check(self, document: Document) -> list[Finding]:
        """Check balance sheet equation."""
        findings: list[Finding] = []
        balance_checks: list[BalanceCheck] = []
        
        for page in document.pages:
            # Only check pages classified as balance sheet
            if page.semantic_section != "balance_sheet":
                # Also check items for balance sheet type
                has_balance_table = any(
                    isinstance(item, Table) 
                    and item.financial_type == FinancialType.BALANCE_SHEET
                    for item in page.items
                )
                if not has_balance_table:
                    continue
            
            for item in page.items:
                if not isinstance(item, Table):
                    continue
                
                table = item
                
                # Skip if not a balance sheet table
                if table.financial_type != FinancialType.BALANCE_SHEET:
                    continue
                
                # Find totals
                assets_total, liabilities_total = self.find_balance_totals(table)
                
                if assets_total is not None and liabilities_total is not None:
                    difference = abs(assets_total - liabilities_total)
                    
                    # Determine severity based on difference
                    # Allow small rounding differences (0.5% tolerance)
                    tolerance = max(abs(assets_total), abs(liabilities_total)) * 0.005
                    
                    if difference > tolerance:
                        severity = Severity.WARNING if difference < tolerance * 10 else Severity.ERROR
                        
                        findings.append(
                            Finding(
                                checker=self.name,
                                page_index=page.page_index,
                                table_id=table.table_id,
                                reason=(
                                    f"Balance sheet equation mismatch: "
                                    f"Assets={assets_total:,.2f}, Liabilities={liabilities_total:,.2f}, "
                                    f"Difference={difference:,.2f}"
                                ),
                                severity=severity,
                            )
                        )
                        
                        balance_checks.append(
                            BalanceCheck(
                                page_index=page.page_index,
                                table_id=table.table_id,
                                assets=assets_total,
                                liabilities=liabilities_total,
                                difference=difference,
                                severity=severity,
                            )
                        )
        
        return findings
