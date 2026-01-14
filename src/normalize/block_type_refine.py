"""Refine block types: detect TOC/dotted leaders and validate tables (V6 Gate B, V7 enhanced)."""

import logging
import re
from typing import Any

from src.schemas.models import Block, BlockType, Table

logger = logging.getLogger(__name__)


def is_toc_page(page_items: list[Block | Table]) -> bool:
    """
    Detect if page is a table of contents (TOC) page (V7 Gate B).
    
    Heuristics:
    - Contains keyword: "sisällysluettelo" / "sisallysluettelo" / "contents"
    - OR contains multiple rows with:
      - Section text + dotted leaders ("....") + page number on right
      - Section numbers like "7.3", "8.4.1", etc.
    
    Args:
        page_items: List of blocks and tables on the page
        
    Returns:
        True if page looks like TOC
    """
    # Collect all text from page
    all_text = ""
    for item in page_items:
        if isinstance(item, Block):
            all_text += " " + item.text
        elif isinstance(item, Table) and item.cells:
            for cell in item.cells:
                all_text += " " + cell.text_raw
    
    text_lower = all_text.lower()
    
    # Check for TOC keywords
    toc_keywords = ["sisällysluettelo", "sisallysluettelo", "contents", "table of contents"]
    if any(keyword in text_lower for keyword in toc_keywords):
        logger.debug("TOC detected: keyword found")
        return True
    
    # Check for TOC pattern: section numbers + dots + page numbers
    # Pattern: "7.3" or "8.4.1" followed by text, dots, and page number
    section_num_pattern = re.compile(r"\d+\.\d+(?:\.\d+)?")  # e.g., "7.3" or "8.4.1"
    dot_pattern = re.compile(r"\.{3,}")  # 3+ dots
    page_num_pattern = re.compile(r"\b\d{1,3}\b")  # Page numbers (1-3 digits)
    
    # Count patterns in text
    section_nums = len(section_num_pattern.findall(all_text))
    dots = len(dot_pattern.findall(all_text))
    page_nums = len(page_num_pattern.findall(all_text))
    
    # TOC heuristics: multiple section numbers + dots + page numbers
    if section_nums >= 3 and dots >= 2 and page_nums >= 3:
        logger.debug(f"TOC detected: section_nums={section_nums}, dots={dots}, page_nums={page_nums}")
        return True
    
    # Check for dotted leaders pattern in tables
    for item in page_items:
        if isinstance(item, Table):
            if detect_toc_pattern(item):
                logger.debug("TOC detected: table pattern")
                return True
    
    return False


def detect_toc_pattern(table: Table) -> bool:
    """
    Detect if table is actually a table of contents (TOC) with dotted leaders.
    
    Heuristics:
    - Contains many dotted lines (`.....`)
    - Page numbers on the right side
    - Few numeric columns
    - Multiple rows with similar structure
    
    Args:
        table: Table to check
        
    Returns:
        True if table looks like TOC
    """
    if not table.cells or len(table.cells) < 3:
        return False
    
    # Count cells with dots
    cells_with_dots = 0
    cells_with_page_numbers = 0
    numeric_cells = 0
    total_cells = len(table.cells)
    
    # Check for dotted leaders pattern
    dot_pattern = re.compile(r"\.{3,}")  # 3+ dots
    
    for cell in table.cells:
        text = cell.text_raw.strip()
        
        # Check for dots
        if dot_pattern.search(text):
            cells_with_dots += 1
        
        # Check for page numbers (right-aligned numbers, often at end of row)
        if re.match(r"^\d+$", text):
            cells_with_page_numbers += 1
        
        # Check for numeric content
        if re.search(r"\d+", text):
            numeric_cells += 1
    
    # TOC heuristics
    dot_ratio = cells_with_dots / total_cells if total_cells > 0 else 0
    page_num_ratio = cells_with_page_numbers / total_cells if total_cells > 0 else 0
    numeric_ratio = numeric_cells / total_cells if total_cells > 0 else 0
    
    # If high dot ratio and page numbers, likely TOC
    is_toc = (dot_ratio > 0.1 and page_num_ratio > 0.1) or (dot_ratio > 0.2)
    
    if is_toc:
        logger.debug(
            f"Table {table.table_id} detected as TOC: "
            f"dot_ratio={dot_ratio:.2f}, page_num_ratio={page_num_ratio:.2f}, numeric_ratio={numeric_ratio:.2f}"
        )
    
    return is_toc


def validate_table_structure(table: Table) -> bool:
    """
    Validate if table has proper table structure.
    
    Rules:
    - Must have at least 2 columns
    - Must have at least 10% numeric values (for financial statements)
    
    Args:
        table: Table to validate
        
    Returns:
        True if table is valid, False if should be converted to text blocks
    """
    if not table.cells:
        return False
    
    # Count columns (unique column indices)
    columns = set(cell.col for cell in table.cells)
    num_columns = len(columns)
    
    # Must have at least 2 columns
    if num_columns < 2:
        logger.debug(f"Table {table.table_id} rejected: only {num_columns} column(s)")
        return False
    
    # Count numeric cells
    numeric_pattern = re.compile(r"[\d,.\-()]+")  # Numbers with formatting
    numeric_cells = sum(1 for cell in table.cells if numeric_pattern.search(cell.text_raw))
    numeric_ratio = numeric_cells / len(table.cells) if table.cells else 0
    
    # For financial statements, expect at least 10% numeric values
    MIN_NUMERIC_RATIO = 0.10
    if numeric_ratio < MIN_NUMERIC_RATIO:
        logger.debug(
            f"Table {table.table_id} rejected: numeric ratio {numeric_ratio:.2f} < {MIN_NUMERIC_RATIO}"
        )
        return False
    
    return True


def convert_toc_to_text_blocks(table: Table, page_index: int) -> list[Block]:
    """
    Convert TOC table to text blocks with list_item type.
    
    Args:
        table: TOC table to convert
        page_index: Page index
        
    Returns:
        List of text blocks
    """
    from src.schemas.models import Block, BlockType, BBox, SourceType
    
    blocks: list[Block] = []
    
    # Group cells by row
    rows: dict[int, list] = {}
    for cell in table.cells:
        if cell.row not in rows:
            rows[cell.row] = []
        rows[cell.row].append(cell)
    
    # Convert each row to a list item block
    for row_idx, row_cells in sorted(rows.items()):
        # Combine cell texts
        texts = [cell.text_raw.strip() for cell in sorted(row_cells, key=lambda c: c.col)]
        text = " ".join(texts).strip()
        
        if not text:
            continue
        
        # Use table bbox for positioning
        bbox = table.bbox
        
        block = Block(
            block_id=f"p{page_index}_b_toc_{row_idx}",
            type=BlockType.TEXT,  # Use 'type' not 'block_type'
            text=text,
            bbox=bbox,
            source=SourceType.OCR,  # Use 'source' not 'source_type'
            semantic_type="list_item",  # V6: Mark as list item
        )
        
        blocks.append(block)
    
    logger.info(f"Converted TOC table {table.table_id} to {len(blocks)} text blocks")
    return blocks


def refine_block_types(
    pages: list[dict[str, Any]], all_tables: dict[int, list[Table]], all_blocks: dict[int, list[Block]]
) -> tuple[dict[int, list[Table]], dict[int, list[Block]]]:
    """
    Refine block types: convert invalid tables to text blocks (V6 Gate B, V7 enhanced).
    
    Args:
        pages: Page data from manifest
        all_tables: Dictionary of page_index -> list of tables
        all_blocks: Dictionary of page_index -> list of blocks
        
    Returns:
        Tuple of (refined_tables, refined_blocks)
    """
    refined_tables: dict[int, list[Table]] = {}
    refined_blocks: dict[int, list[Block]] = {}
    
    for page_data in pages:
        page_index = page_data["page_index"]
        tables = all_tables.get(page_index, [])
        blocks = all_blocks.get(page_index, [])
        
        # V7: Check if page is TOC at page level (before checking individual tables)
        page_items_for_toc_check: list[Block | Table] = list(blocks) + list(tables)
        is_page_toc = is_toc_page(page_items_for_toc_check)
        
        refined_page_tables: list[Table] = []
        refined_page_blocks = blocks.copy()
        
        for table in tables:
            # V7: If page is TOC, convert all tables to list items
            if is_page_toc:
                # Convert TOC table to text blocks
                toc_blocks = convert_toc_to_text_blocks(table, page_index)
                refined_page_blocks.extend(toc_blocks)
                logger.info(f"Page {page_index}: Converted TOC table {table.table_id} to text blocks (page-level TOC detected)")
                continue
            
            # Check if table is actually TOC (table-level detection)
            if detect_toc_pattern(table):
                # Convert TOC to text blocks
                toc_blocks = convert_toc_to_text_blocks(table, page_index)
                refined_page_blocks.extend(toc_blocks)
                logger.info(f"Page {page_index}: Converted TOC table {table.table_id} to text blocks")
                continue
            
            # Validate table structure
            if not validate_table_structure(table):
                # Convert invalid table to text blocks
                # Simple conversion: combine all cell texts
                all_texts = [cell.text_raw.strip() for cell in table.cells if cell.text_raw.strip()]
                if all_texts:
                    from src.schemas.models import Block, BlockType, BBox, SourceType
                    
                    combined_text = " ".join(all_texts)
                    text_block = Block(
                        block_id=f"p{page_index}_b_from_table_{table.table_id}",
                        type=BlockType.TEXT,  # Use 'type' not 'block_type'
                        text=combined_text,
                        bbox=table.bbox,
                        source=SourceType.OCR,  # Use 'source' not 'source_type'
                        semantic_type="text",
                    )
                    refined_page_blocks.append(text_block)
                    logger.info(f"Page {page_index}: Converted invalid table {table.table_id} to text block")
                continue
            
            # Keep valid table
            refined_page_tables.append(table)
        
        refined_tables[page_index] = refined_page_tables
        refined_blocks[page_index] = refined_page_blocks
    
    return refined_tables, refined_blocks
