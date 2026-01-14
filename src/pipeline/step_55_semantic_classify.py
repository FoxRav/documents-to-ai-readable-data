"""Step 55: Semantic classification (layout + financial statement types) - V6 enhanced."""

import logging
import re
from pathlib import Path
from typing import Any

from src.schemas.models import Block, Document, FinancialType, Page, Table

logger = logging.getLogger(__name__)


# Keywords for financial statement classification (Finnish and English)
BALANCE_SHEET_KEYWORDS = [
    "tase",
    "balance sheet",
    "statement of financial position",
    "vastaavaa",
    "vastattavaa",
    "omavaraisuusaste",
    "varat",
    "velat",
]

INCOME_STATEMENT_KEYWORDS = [
    "tuloslaskelma",
    "income statement",
    "profit or loss",
    "toimintatuotot",
    "toimintakulut",
    "verotulot",
    "tulos",
]

CASH_FLOW_KEYWORDS = [
    "rahoituslaskelma",
    "cash flow",
    "rahavirtalaskelma",
    "cash_assets",  # käteisvarat
]

NOTES_KEYWORDS = [
    "liitetiedot",
    "notes",
    "liite",
    "selitykset",
    "explanatory notes",
]

ACCOUNTING_POLICIES_KEYWORDS = [
    "tilinpäätöksen laatimisperiaatteet",
    "accounting policies",
    "financial_statement_principles",  # tilinpäätösperiaatteet
]


def classify_financial_type(text: str) -> tuple[FinancialType | None, list[str]]:
    """Classify financial statement type based on keywords."""
    text_lower = text.lower()
    evidence: list[str] = []

    # Check balance sheet
    for keyword in BALANCE_SHEET_KEYWORDS:
        if keyword in text_lower:
            evidence.append(f"keyword:{keyword}")
            return FinancialType.BALANCE_SHEET, evidence

    # Check income statement
    for keyword in INCOME_STATEMENT_KEYWORDS:
        if keyword in text_lower:
            evidence.append(f"keyword:{keyword}")
            return FinancialType.INCOME_STATEMENT, evidence

    # Check cash flow
    for keyword in CASH_FLOW_KEYWORDS:
        if keyword in text_lower:
            evidence.append(f"keyword:{keyword}")
            return FinancialType.CASH_FLOW_STATEMENT, evidence

    # Check notes
    for keyword in NOTES_KEYWORDS:
        if keyword in text_lower:
            evidence.append(f"keyword:{keyword}")
            return FinancialType.NOTES, evidence

    # Check accounting policies
    for keyword in ACCOUNTING_POLICIES_KEYWORDS:
        if keyword in text_lower:
            evidence.append(f"keyword:{keyword}")
            return FinancialType.ACCOUNTING_POLICIES, evidence

    return None, []


def classify_table_structure(table: Table) -> tuple[FinancialType | None, list[str]]:
    """Classify table based on structure heuristics."""
    evidence: list[str] = []

    # Check for balance sheet structure: "Vastaavaa" / "Vastattavaa" columns
    if table.cells:
        # Look for common balance sheet terms in first few cells
        first_cells_text = " ".join([cell.text_raw.lower() for cell in table.cells[:10]])
        if any(term in first_cells_text for term in ["vastaavaa", "vastattavaa", "varat", "velat"]):
            evidence.append("structure:balance_sheet_columns")
            return FinancialType.BALANCE_SHEET, evidence

        # Check for income statement: "2024/2023" columns + income/expense rows
        if "2024" in first_cells_text or "2023" in first_cells_text:
            if any(term in first_cells_text for term in ["tuotot", "kulut", "tulos"]):
                evidence.append("structure:income_statement_columns")
                return FinancialType.INCOME_STATEMENT, evidence

    return None, []


# V6: Semantic section keywords
TOC_KEYWORDS = ["sisällysluettelo", "contents", "table of contents", "sisällys"]
COVER_KEYWORDS = ["tilinpäätös", "financial statement", "annual report", "vuosikertomus"]
MANAGEMENT_REPORT_KEYWORDS = ["johtajan kertomus", "management report", "hallituksen kertomus"]


def classify_page_section(page: Page) -> tuple[str | None, float]:
    """
    Classify page semantic section (V6: expanded taxonomy, V7: enhanced TOC detection).
    
    Returns:
        Tuple of (semantic_section, confidence)
    """
    # V7: Use page-level TOC detection first
    from src.normalize.block_type_refine import is_toc_page
    
    if is_toc_page(page.items):
        logger.debug(f"Page {page.page_index}: TOC detected via page-level heuristics")
        return "toc", 0.9
    
    # Collect text from first few blocks
    text_samples: list[str] = []
    for item in page.items[:10]:  # Check more items
        if isinstance(item, Block):
            text_samples.append(item.text)
        elif isinstance(item, Table) and item.cells:
            # Also check table headers
            header_text = " ".join([cell.text_raw for cell in item.cells if cell.row == 0][:5])
            text_samples.append(header_text)

    combined_text = " ".join(text_samples).lower()

    # V6: Check for cover page (usually first page with title)
    if page.page_index == 0:
        if any(keyword in combined_text for keyword in COVER_KEYWORDS):
            return "cover", 0.9

    # V6: Check for TOC (table of contents) - fallback to keyword check
    if any(keyword in combined_text for keyword in TOC_KEYWORDS):
        # Also check if page has list_item blocks (from TOC conversion)
        has_list_items = any(
            isinstance(item, Block) and item.semantic_type == "list_item" for item in page.items
        )
        if has_list_items or any("..." in text for text in text_samples):
            return "toc", 0.85

    # V6: Check for management report
    if any(keyword in combined_text for keyword in MANAGEMENT_REPORT_KEYWORDS):
        return "management_report", 0.8

    # Check for financial statement sections
    if any(keyword in combined_text for keyword in NOTES_KEYWORDS):
        return "notes", 0.8

    if any(keyword in combined_text for keyword in ["tase", "balance sheet"]):
        return "balance_sheet", 0.7

    if any(keyword in combined_text for keyword in ["tuloslaskelma", "income statement"]):
        return "income_statement", 0.7

    if any(keyword in combined_text for keyword in CASH_FLOW_KEYWORDS):
        return "cash_flow_statement", 0.7

    if any(keyword in combined_text for keyword in ACCOUNTING_POLICIES_KEYWORDS):
        return "accounting_policies", 0.7

    # Default: appendix if later pages
    if page.page_index > len(page.items) * 0.8:  # Rough heuristic
        return "appendix", 0.3

    return None, 0.0


def parse_toc_target_page(text: str) -> int | None:
    """
    Parse target page number from TOC entry text (V8 Gate C).
    
    Extracts page number from end of TOC entry, e.g.:
    - "8.3 Tase ... 134" → 134
    - "Tuloslaskelma 45" → 45
    - "7.3 Notes.....89" → 89
    
    Returns:
        Page number as int, or None if not found
    """
    if not text or not text.strip():
        return None
    
    # Remove trailing whitespace
    text = text.strip()
    
    # Pattern: look for 1-3 digit number at end of line, possibly after dots
    # Match patterns like "... 134", "....89", " 45"
    patterns = [
        r"\.{2,}\s*(\d{1,3})\s*$",  # Dots followed by number
        r"\s+(\d{1,3})\s*$",  # Space followed by number at end
        r"(\d{1,3})\s*$",  # Just number at end
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                page_num = int(match.group(1))
                # Sanity check: page numbers typically 1-500
                if 1 <= page_num <= 500:
                    return page_num
            except ValueError:
                continue
    
    return None


def calculate_page_number_offset(document: "Document") -> int:
    """
    Calculate offset between logical page numbers and PDF page indices (V8 Gate C).
    
    Strategy:
    1. Look for standalone page numbers in footer/header areas
    2. Check for "sivu X" / "page X" patterns
    3. Use TOC first entry as calibration point
    4. Default to 2 for Finnish municipal reports
    
    Returns:
        Offset value: pdf_page_index = toc_page_number + offset
        (Typically negative: if TOC says "page 127", PDF index might be 125)
    """
    candidates: list[tuple[int, int, str]] = []  # (pdf_idx, logical_num, source)
    
    # Strategy 1: Look for page numbers in footer area (bottom 15% of page)
    for page in document.pages[3:15]:  # Skip first few pages (cover/TOC)
        if not page.items:
            continue
        
        page_height = page.height
        footer_threshold = page_height * 0.85  # Bottom 15%
        
        for item in page.items:
            if isinstance(item, Block):
                # Check if in footer area
                if item.bbox.y0 > footer_threshold or item.bbox.y1 > footer_threshold:
                    text = item.text.strip()
                    
                    # Pattern 1: Standalone number (common in footers)
                    match = re.match(r"^(\d{1,3})$", text)
                    if match:
                        logical_page = int(match.group(1))
                        if 1 <= logical_page <= 200:
                            candidates.append((page.page_index, logical_page, "footer_number"))
                    
                    # Pattern 2: "sivu X" or "page X"
                    match = re.search(r"(?:sivu|page)\s*(\d{1,3})", text.lower())
                    if match:
                        logical_page = int(match.group(1))
                        if 1 <= logical_page <= 200:
                            candidates.append((page.page_index, logical_page, "sivu_pattern"))
    
    # Strategy 2: Use header area (top 10%)
    for page in document.pages[3:15]:
        if not page.items:
            continue
        
        page_height = page.height
        header_threshold = page_height * 0.10  # Top 10%
        
        for item in page.items:
            if isinstance(item, Block):
                if item.bbox.y0 < header_threshold:
                    text = item.text.strip()
                    match = re.match(r"^(\d{1,3})$", text)
                    if match:
                        logical_page = int(match.group(1))
                        if 1 <= logical_page <= 200:
                            candidates.append((page.page_index, logical_page, "header_number"))
    
    # Calculate offset from candidates
    if candidates:
        # Calculate offsets and find most common
        offsets = [pdf_idx - logical for pdf_idx, logical, _ in candidates]
        if offsets:
            # Use median offset (more robust to outliers)
            median_offset = int(sorted(offsets)[len(offsets) // 2])
            logger.info(
                f"V8 Offset calculation: found {len(candidates)} candidates, "
                f"median offset = {median_offset}"
            )
            return median_offset
    
    # Strategy 3: Estimate from TOC structure
    # If we have TOC pages, assume they start at page 1-3
    toc_pages = [p for p in document.pages if p.semantic_section == "toc"]
    if toc_pages and len(toc_pages) > 0:
        first_toc_idx = toc_pages[0].page_index
        # TOC usually starts at logical page 1-2
        estimated_offset = first_toc_idx - 1
        logger.info(f"V8 Offset calculation: estimated from TOC position, offset = {estimated_offset}")
        return estimated_offset
    
    # Default for Finnish municipal reports
    logger.warning("V8 Offset calculation: using default offset = 2")
    return 2


def extract_financial_types_from_toc(page: Page) -> dict[str, tuple[FinancialType, int | None]]:
    """
    Extract financial types from TOC page with target pages (V7/V8 Gate C).
    
    Looks for TOC entries that mention financial statement types and extracts
    target page numbers.
    
    Returns:
        Dictionary mapping TOC entry text to (FinancialType, target_page)
    """
    financial_types: dict[str, tuple[FinancialType, int | None]] = {}
    
    # Collect all text from page items with their texts
    item_texts: list[str] = []
    for item in page.items:
        if isinstance(item, Block):
            item_texts.append(item.text)
        elif isinstance(item, Table) and item.cells:
            for cell in item.cells:
                item_texts.append(cell.text_raw)
    
    all_text = " ".join(item_texts)
    text_lower = all_text.lower()
    
    # Map keywords to financial types
    keyword_mapping = {
        "tuloslaskelma": FinancialType.INCOME_STATEMENT,
        "income statement": FinancialType.INCOME_STATEMENT,
        "rahoituslaskelma": FinancialType.CASH_FLOW_STATEMENT,
        "cash flow": FinancialType.CASH_FLOW_STATEMENT,
        "tase": FinancialType.BALANCE_SHEET,
        "balance sheet": FinancialType.BALANCE_SHEET,
        "liitetiedot": FinancialType.NOTES,
        "notes": FinancialType.NOTES,
    }
    
    # Find keywords in individual items to get proper context
    for item_text in item_texts:
        item_lower = item_text.lower()
        for keyword, financial_type in keyword_mapping.items():
            if keyword in item_lower:
                # V8: Extract target page from this TOC entry
                target_page = parse_toc_target_page(item_text)
                
                # Try to extract the full TOC entry (e.g., "7.3 Tuloslaskelma ... 134")
                pattern = re.compile(rf"(\d+\.\d+(?:\.\d+)?\s*{re.escape(keyword)}[^\n]*)", re.IGNORECASE)
                matches = pattern.findall(item_text)
                if matches:
                    for match in matches:
                        financial_types[match] = (financial_type, target_page)
                else:
                    # Fallback: just use keyword
                    financial_types[keyword] = (financial_type, target_page)
    
    return financial_types


def classify_element_semantic_type(item: Block | Table, page_index: int, is_first_item: bool = False) -> str | None:
    """
    Classify element semantic type (V6).
    
    Returns:
        semantic_type: title, section_header, text, list_item, table, page_header, page_footer
    """
    if isinstance(item, Block):
        # Check if already classified (e.g., from TOC conversion)
        if item.semantic_type:
            return item.semantic_type
        
        text_lower = item.text.lower().strip()
        
        # Title: first item on page, or very short text, or all caps
        if is_first_item and len(text_lower) < 100:
            if text_lower.isupper() or len(text_lower.split()) <= 5:
                return "title"
        
        # Section header: short text, often bold, at start of line
        if len(text_lower) < 50 and (item.font_stats and item.font_stats.bold):
            if any(keyword in text_lower for keyword in ["tase", "tuloslaskelma", "liite", "notes"]):
                return "section_header"
        
        # List item: already marked or starts with bullet/number
        if item.semantic_type == "list_item" or re.match(r"^[\d•\-\*]\s+", text_lower):
            return "list_item"
        
        # Default: text
        return "text"
    
    elif isinstance(item, Table):
        return "table"
    
    return None


def build_toc_target_map(
    document: Document, page_offset: int
) -> dict[int, tuple[str, FinancialType]]:
    """
    Build a map of PDF page indices to expected semantic sections from TOC (V8).
    
    Returns:
        Dictionary: pdf_page_index -> (semantic_section, financial_type)
    """
    target_map: dict[int, tuple[str, FinancialType]] = {}
    
    # Map financial_type to semantic_section
    financial_type_to_section = {
        FinancialType.INCOME_STATEMENT: "income_statement",
        FinancialType.BALANCE_SHEET: "balance_sheet",
        FinancialType.CASH_FLOW_STATEMENT: "cash_flow_statement",
        FinancialType.NOTES: "notes",
        FinancialType.ACCOUNTING_POLICIES: "accounting_policies",
        FinancialType.MANAGEMENT_REPORT: "management_report",
    }
    
    for page in document.pages:
        if page.semantic_section != "toc":
            continue
        
        # Extract financial types from TOC page
        financial_types = extract_financial_types_from_toc(page)
        
        for toc_text, (fin_type, toc_page) in financial_types.items():
            if toc_page is None:
                continue
            
            # Calculate PDF page index
            pdf_page_idx = toc_page + page_offset
            
            if pdf_page_idx >= 0:
                section = financial_type_to_section.get(fin_type, "notes")
                target_map[pdf_page_idx] = (section, fin_type)
                logger.debug(f"TOC target: '{toc_text[:40]}' -> PDF page {pdf_page_idx} = {section}")
    
    return target_map


def classify_page_with_hard_rules(page: Page) -> tuple[str | None, float]:
    """
    Classify page using hard rules based on content (V8).
    
    Looks for strong indicators of financial statement pages:
    - Balance sheet: VASTAAVAA, VASTATTAVAA, PYSYVÄT VASTAAVAT
    - Income statement: TOIMINTATUOTOT, TOIMINTAKULUT, TUOTOT, KULUT
    - Cash flow: RAHAVIRTALASKELMA keywords
    
    Returns:
        Tuple of (semantic_section, confidence)
    """
    # Collect all text from page
    all_text = ""
    for item in page.items:
        if isinstance(item, Block):
            all_text += " " + item.text
        elif isinstance(item, Table) and item.cells:
            for cell in item.cells:
                all_text += " " + cell.text_raw
    
    text_upper = all_text.upper()
    text_lower = all_text.lower()
    
    # Balance sheet hard rules (Finnish municipal reports)
    balance_sheet_indicators = [
        "VASTAAVAA",
        "VASTATTAVAA", 
        "PYSYVÄT VASTAAVAT",
        "VAIHTUVAT VASTAAVAT",
        "OMA PÄÄOMA",
        "VIERAS PÄÄOMA",
    ]
    balance_matches = sum(1 for ind in balance_sheet_indicators if ind in text_upper)
    if balance_matches >= 2:
        return "balance_sheet", 0.9
    
    # Income statement hard rules
    income_indicators = [
        "TOIMINTATUOTOT",
        "TOIMINTAKULUT",
        "VUOSIKATE",
        "TILIKAUDEN TULOS",
        "SATUNNAISET TUOTOT",
        "SATUNNAISET KULUT",
    ]
    income_matches = sum(1 for ind in income_indicators if ind in text_upper)
    if income_matches >= 2:
        return "income_statement", 0.9
    
    # Cash flow hard rules
    cash_flow_indicators = [
        "TOIMINNAN RAHAVIRTA",
        "INVESTOINTIEN RAHAVIRTA",
        "RAHOITUKSEN RAHAVIRTA",
        "RAHAVAROJEN MUUTOS",
    ]
    cash_matches = sum(1 for ind in cash_flow_indicators if ind in text_upper)
    if cash_matches >= 2:
        return "cash_flow_statement", 0.9
    
    # Notes section indicators
    if "liitetiedot" in text_lower or "liite " in text_lower:
        # Check if this is actual notes content (not just TOC reference)
        if len(all_text) > 500:  # Notes pages typically have more content
            return "notes", 0.7
    
    return None, 0.0


def classify_document(document: Document) -> Document:
    """
    Apply semantic classification to all pages, blocks, and tables (V6/V8/V9: enhanced).
    
    V8/V9 additions:
    - Calculate page number offset (document page -> PDF index)
    - Build TOC target map for TOC-guided classification
    - Apply hard rules for financial statement page detection
    - Use TOC targets to override fallback classifications
    
    Ensures semantic_section and semantic_type are not null.
    """
    logger.info("V8/V9: Applying semantic classification with TOC-guided targeting...")

    pages_classified = 0
    elements_classified = 0

    # First pass: initial page section classification (for TOC detection)
    for page in document.pages:
        semantic_section, confidence = classify_page_section(page)
        if semantic_section:
            page.semantic_section = semantic_section
            page.semantic_confidence = confidence
            pages_classified += 1
        else:
            if page.page_index == 0:
                page.semantic_section = "cover"
                page.semantic_confidence = 0.5
            else:
                page.semantic_section = "appendix"  # Temporary, will be refined
                page.semantic_confidence = 0.1

    # V8: Calculate page number offset
    page_offset = calculate_page_number_offset(document)
    document.page_number_offset = page_offset
    logger.info(f"V8: Page number offset = {page_offset}")
    
    # V8/V9: Build TOC target map
    toc_target_map = build_toc_target_map(document, page_offset)
    if toc_target_map:
        logger.info(f"V8: Built TOC target map with {len(toc_target_map)} target pages: {list(toc_target_map.keys())[:10]}")
    
    # Second pass: refine classification using TOC targets and hard rules
    for page in document.pages:
        # Skip TOC and cover pages
        if page.semantic_section in ("toc", "cover"):
            continue
        
        # V9: Check if this page is a TOC target
        if page.page_index in toc_target_map:
            toc_section, toc_fin_type = toc_target_map[page.page_index]
            page.semantic_section = toc_section
            page.semantic_confidence = 0.85
            logger.info(f"Page {page.page_index}: TOC-guided classification -> {toc_section}")
            continue
        
        # V9: Apply hard rules for financial statement detection
        hard_section, hard_confidence = classify_page_with_hard_rules(page)
        if hard_section and hard_confidence > 0.5:
            page.semantic_section = hard_section
            page.semantic_confidence = hard_confidence
            logger.debug(f"Page {page.page_index}: Hard rules classification -> {hard_section}")
            continue
        
        # Fallback: check if current classification is weak
        if page.semantic_confidence < 0.3:
            # Try content-based classification again
            semantic_section, confidence = classify_page_section(page)
            if semantic_section and confidence > page.semantic_confidence:
                page.semantic_section = semantic_section
                page.semantic_confidence = confidence

    # Second pass: classify elements and apply offset
    for page in document.pages:
        # V7/V8 Gate C: Extract financial_type from TOC if page is TOC
        financial_types_from_toc: dict[str, tuple[FinancialType, int | None]] = {}
        if page.semantic_section == "toc":
            financial_types_from_toc = extract_financial_types_from_toc(page)
            if financial_types_from_toc:
                logger.debug(f"Page {page.page_index}: Extracted financial types from TOC: {list(financial_types_from_toc.keys())}")
        
        # V6: Classify blocks and tables with semantic_type
        for idx, item in enumerate(page.items):
            is_first_item = idx == 0
            
            if isinstance(item, Block):
                # V6: Set semantic_type
                semantic_type = classify_element_semantic_type(item, page.page_index, is_first_item)
                if semantic_type:
                    item.semantic_type = semantic_type
                    elements_classified += 1
                else:
                    item.semantic_type = "text"  # Default
                
                # V7/V8 Gate C: Classify financial type (TOC-based or text-based)
                financial_type: FinancialType | None = None
                evidence: list[str] = []
                target_page: int | None = None
                
                # If page is TOC, try to match item text to TOC entries
                if page.semantic_section == "toc" and financial_types_from_toc:
                    for toc_text, (ft, tp) in financial_types_from_toc.items():
                        if toc_text.lower() in item.text.lower():
                            financial_type = ft
                            target_page = tp
                            evidence = [f"toc_entry:{toc_text}"]
                            break
                
                # Fallback to text-based classification
                if not financial_type:
                    financial_type, evidence = classify_financial_type(item.text)
                
                if financial_type:
                    item.financial_type = financial_type
                    item.classification_evidence = evidence
                
                # V8: Set target page from TOC entry and calculate PDF index
                if target_page is not None:
                    item.toc_target_page = target_page
                    # Apply offset to get PDF page index
                    # pdf_page_index = toc_page_number + offset
                    pdf_target = target_page + page_offset
                    # Allow any non-negative value (even if page not in current run)
                    if pdf_target >= 0:
                        item.pdf_target_page = pdf_target
                        logger.debug(
                            f"TOC entry '{item.text[:30]}...' -> page {target_page} -> PDF index {pdf_target}"
                        )

            elif isinstance(item, Table):
                # V6: Set semantic_type
                item.semantic_type = "table"
                elements_classified += 1
                
                # Classify table structure
                financial_type, evidence = classify_table_structure(item)
                if financial_type:
                    item.financial_type = financial_type
                    item.classification_evidence = evidence

                # Also check table text content
                if not financial_type and item.cells:
                    # Get text from first row (often headers)
                    header_text = " ".join([cell.text_raw for cell in item.cells if cell.row == 0][:5])
                    financial_type, evidence = classify_financial_type(header_text)
                    if financial_type:
                        item.financial_type = financial_type
                        item.classification_evidence = evidence

    logger.info(
        f"V6: Semantic classification completed: {pages_classified}/{len(document.pages)} pages, "
        f"{elements_classified} elements classified"
    )
    return document


if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python step_55_semantic_classify.py <document_json_path>")
        sys.exit(1)

    document_path = Path(sys.argv[1])

    with open(document_path, "r", encoding="utf-8") as f:
        document_dict = json.load(f)

    document = Document.model_validate(document_dict)
    classified = classify_document(document)

    # Save classified document
    output_path = document_path.parent / "document_classified.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(classified.model_dump_json(indent=2))

    print(f"Classified document saved to {output_path}")
