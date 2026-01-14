"""Step 10: Native text extraction (for native/mixed pages)."""

import json
import logging
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

from src.schemas.models import Block, BlockType, BBox, FontStats, SourceType

logger = logging.getLogger(__name__)


def extract_font_stats(page: fitz.Page, block: tuple) -> FontStats | None:
    """Extract font statistics from a text block."""
    try:
        # PyMuPDF block format: (x0, y0, x1, y1, "text", block_no, block_type, font_size, font_name)
        if len(block) >= 8:
            font_size = block[7] if isinstance(block[7], (int, float)) else None
            font_name = block[8] if len(block) > 8 and isinstance(block[8], str) else None

            # Try to detect bold/italic from font name (heuristic)
            bold = False
            italic = False
            if font_name:
                font_lower = font_name.lower()
                bold = "bold" in font_lower or "black" in font_lower
                italic = "italic" in font_lower or "oblique" in font_lower

            return FontStats(size=font_size, family=font_name, bold=bold, italic=italic)
    except Exception as e:
        logger.debug(f"Error extracting font stats: {e}")
    return None


def extract_native_text_blocks(
    pdf_path: Path, page_index: int, output_dir: Path
) -> list[Block]:
    """Extract native text blocks from a page."""
    logger.debug(f"Extracting native text from page {page_index}")

    blocks: list[Block] = []

    # Use PyMuPDF for block extraction with bbox
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    page_rect = page.rect

    # Get text blocks
    text_blocks = page.get_text("blocks")

    block_id_counter = 0
    for block in text_blocks:
        # block format: (x0, y0, x1, y1, "text", block_no, block_type, font_size, font_name)
        if len(block) >= 6 and block[6] == 0:  # type 0 = text
            x0, y0, x1, y1 = block[0], block[1], block[2], block[3]
            text = block[4] if len(block) > 4 else ""

            # Skip empty blocks
            if not text.strip():
                continue

            # Create bbox
            bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)

            # Extract font stats
            font_stats = extract_font_stats(page, block)

            # Determine block type (heuristic)
            block_type = BlockType.TEXT
            text_lower = text.strip().lower()
            if len(text) < 100 and (
                text_lower.isupper() or font_stats and font_stats.size and font_stats.size > 12
            ):
                block_type = BlockType.TITLE
            elif text_lower.startswith(("•", "-", "1.", "2.", "3.")):
                block_type = BlockType.LIST_ITEM

            block_id = f"p{page_index}_b{block_id_counter}"
            block_obj = Block(
                block_id=block_id,
                type=block_type,
                text=text.strip(),
                bbox=bbox,
                source=SourceType.NATIVE,
                confidence=1.0,
                font_stats=font_stats,
            )

            blocks.append(block_obj)
            block_id_counter += 1

    doc.close()

    # Save to JSONL
    output_file = output_dir / f"page_{page_index:04d}.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for block in blocks:
            f.write(block.model_dump_json() + "\n")

    logger.info(f"Extracted {len(blocks)} native text blocks from page {page_index}")
    return blocks


def process_native_pages(
    pdf_path: Path, manifest: dict, output_dir: Path
) -> dict[int, list[Block]]:
    """Process all native/mixed pages."""
    output_dir.mkdir(parents=True, exist_ok=True)

    all_blocks: dict[int, list[Block]] = {}

    pages = manifest.get("pages", [])
    for page_data in pages:
        page_index = page_data["page_index"]
        mode = page_data.get("mode", "native")

        # Extract native text for native and mixed pages
        if mode in ("native", "mixed"):
            try:
                blocks = extract_native_text_blocks(pdf_path, page_index, output_dir)
                all_blocks[page_index] = blocks
            except Exception as e:
                logger.error(f"Error extracting native text from page {page_index}: {e}")
                all_blocks[page_index] = []

    return all_blocks


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python step_10_native_text.py <pdf_path> <manifest_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    output_dir = Path("data/10_work/blocks_native")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    process_native_pages(pdf_path, manifest, output_dir)
