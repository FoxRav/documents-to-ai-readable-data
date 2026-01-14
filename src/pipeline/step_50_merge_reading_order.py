"""Step 50: Merge all elements and establish reading order."""

import logging
from pathlib import Path
from typing import Any

from src.schemas.models import Block, Document, Page, PDFInfo, Table

logger = logging.getLogger(__name__)


def remove_header_footer(blocks: list[Block], page_height: float) -> list[Block]:
    """Remove header/footer regions (heuristic: top/bottom 10% of page)."""
    header_threshold = page_height * 0.1
    footer_threshold = page_height * 0.9

    filtered: list[Block] = []
    for block in blocks:
        # Skip if in header/footer region
        if block.bbox.y0 < header_threshold or block.bbox.y1 > footer_threshold:
            continue
        filtered.append(block)

    return filtered


def cluster_columns(items: list[Block | Table], page_width: float) -> list[list[Block | Table]]:
    """Cluster items into columns (1-2 columns typical)."""
    if not items:
        return []

    # Simple heuristic: if items are mostly on left or right half, assume single column
    # Otherwise, cluster by x-coordinate

    # Calculate x-centers
    x_centers = []
    for item in items:
        if isinstance(item, Block):
            x_center = (item.bbox.x0 + item.bbox.x1) / 2
        else:  # Table
            x_center = (item.bbox.x0 + item.bbox.x1) / 2
        x_centers.append(x_center)

    if not x_centers:
        return [items]

    # Simple clustering: if items span more than 60% of page width, likely 2 columns
    min_x = min(x_centers)
    max_x = max(x_centers)
    span_ratio = (max_x - min_x) / page_width if page_width > 0 else 0

    if span_ratio < 0.6:
        # Single column
        return [items]
    else:
        # Two columns: split at midpoint
        midpoint = page_width / 2
        left_column: list[Block | Table] = []
        right_column: list[Block | Table] = []

        for item, x_center in zip(items, x_centers):
            if x_center < midpoint:
                left_column.append(item)
            else:
                right_column.append(item)

        # Sort each column by y-coordinate
        left_column.sort(key=lambda i: i.bbox.y0 if isinstance(i, Block) else i.bbox.y0)
        right_column.sort(key=lambda i: i.bbox.y0 if isinstance(i, Block) else i.bbox.y0)

        return [left_column, right_column]


def establish_reading_order(items: list[Block | Table]) -> list[Block | Table]:
    """Establish reading order: cluster by columns, then sort by y-coordinate within columns."""
    if not items:
        return []

    # Get page dimensions from first item
    if isinstance(items[0], Block):
        page_width = items[0].bbox.x1
        page_height = items[0].bbox.y1
    else:  # Table
        page_width = items[0].bbox.x1
        page_height = items[0].bbox.y1

    # Cluster into columns
    columns = cluster_columns(items, page_width)

    # Merge columns in reading order (left to right, top to bottom)
    ordered: list[Block | Table] = []

    if len(columns) == 1:
        # Single column: just sort by y
        ordered = sorted(columns[0], key=lambda i: i.bbox.y0 if isinstance(i, Block) else i.bbox.y0)
    else:
        # Multi-column: interleave by y-coordinate
        # Simple approach: process items in y-order, but maintain column context
        all_items_with_col: list[tuple[int, Block | Table]] = []
        for col_idx, col_items in enumerate(columns):
            for item in col_items:
                y0 = item.bbox.y0 if isinstance(item, Block) else item.bbox.y0
                all_items_with_col.append((col_idx, y0, item))

        # Sort by y, then by column (left first)
        all_items_with_col.sort(key=lambda x: (x[1], x[0]))
        ordered = [item for _, _, item in all_items_with_col]

    return ordered


def merge_page_elements(
    page_index: int,
    page_width: float,
    page_height: float,
    blocks: list[Block],
    tables: list[Table],
    is_toc_page: bool = False,
) -> Page:
    """
    Merge all elements for a page and establish reading order.
    
    Args:
        page_index: Page index
        page_width: Page width
        page_height: Page height
        blocks: Blocks for the page
        tables: Tables for the page
        is_toc_page: Whether this is a TOC page (V7: don't remove header/footer for TOC)
    """
    # Combine blocks and tables
    all_items: list[Block | Table] = list(blocks) + list(tables)

    # Remove header/footer (but not for TOC pages - they need all content)
    if is_toc_page:
        text_blocks = blocks  # Keep all blocks for TOC
    else:
        text_blocks = remove_header_footer(blocks, page_height)
    # Keep all tables (they might be in header/footer, but we'll keep them for now)

    # Recombine
    all_items = list(text_blocks) + list(tables)

    # Establish reading order
    ordered_items = establish_reading_order(all_items)

    # Create Page
    page = Page(
        page_index=page_index,
        width=page_width,
        height=page_height,
        items=ordered_items,
    )

    return page


def merge_document(
    manifest: dict[str, Any],
    all_blocks: dict[int, list[Block]],
    all_tables: dict[int, list[Table]],
    ocr_quality_metrics: dict[int, dict[str, Any]] | None = None,
) -> Document:
    """
    Merge all pages into a complete document.
    
    Args:
        manifest: Page manifest
        all_blocks: Blocks per page
        all_tables: Tables per page
        ocr_quality_metrics: OCR quality metrics per page (V7)
    """
    pages_data = manifest.get("pages", [])
    pdf_info = manifest.get("pdf", {})

    pages: list[Page] = []
    empty_pages: list[int] = []

    for page_data in pages_data:
        page_index = page_data["page_index"]
        page_width = page_data["width"]
        page_height = page_data["height"]

        blocks = all_blocks.get(page_index, [])
        tables = all_tables.get(page_index, [])
        
        # V7: Check if page is TOC (before merging, to avoid removing header/footer)
        from src.normalize.block_type_refine import is_toc_page
        page_items_for_toc = list(blocks) + list(tables)
        is_toc = is_toc_page(page_items_for_toc)

        page = merge_page_elements(page_index, page_width, page_height, blocks, tables, is_toc_page=is_toc)
        
        # V7: Add OCR quality metrics if available
        if ocr_quality_metrics and page_index in ocr_quality_metrics:
            page.ocr_quality = ocr_quality_metrics[page_index]
        
        # V2: Track empty pages
        if len(page.items) == 0:
            empty_pages.append(page_index)
        
        pages.append(page)

    # V2: Warn about empty pages
    if empty_pages:
        logger.warning(f"⚠️ V2 VALIDATION: {len(empty_pages)} pages have no items: {empty_pages[:10]}{'...' if len(empty_pages) > 10 else ''}")
        logger.warning("This indicates Step 41B (OCR text) may not have extracted data properly")

    pdf_info_obj = PDFInfo(
        filename=pdf_info.get("filename", "unknown.pdf"),
        pages=len(pages),
    )

    document = Document(pdf=pdf_info_obj, pages=pages)

    return document


if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python step_50_merge_reading_order.py <manifest_path>")
        sys.exit(1)

    manifest_path = Path(sys.argv[1])

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # This would typically load blocks and tables from previous steps
    # For standalone testing, create empty structures
    all_blocks: dict[int, list[Block]] = {}
    all_tables: dict[int, list[Table]] = {}

    document = merge_document(manifest, all_blocks, all_tables, ocr_quality_metrics=None)
    print(f"Merged document with {len(document.pages)} pages")
