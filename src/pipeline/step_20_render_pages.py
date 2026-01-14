"""Step 20: Render pages to PNG (for scan/mixed pages)."""

import logging
from pathlib import Path
from typing import Any

from pdf2image import convert_from_path

from src.pipeline.config import get_settings

logger = logging.getLogger(__name__)


def render_page(
    pdf_path: Path, page_index: int, dpi: int, output_dir: Path, poppler_path: Path | None = None
) -> Path | None:
    """Render a single page to PNG."""
    try:
        # Convert single page
        pages = convert_from_path(
            pdf_path,
            first_page=page_index + 1,  # pdf2image uses 1-based indexing
            last_page=page_index + 1,
            dpi=dpi,
            poppler_path=str(poppler_path) if poppler_path else None,
        )

        if not pages:
            logger.warning(f"No pages rendered for page {page_index}")
            return None

        # Save PNG
        output_file = output_dir / f"page_{page_index:04d}.png"
        pages[0].save(output_file, "PNG")
        logger.debug(f"Rendered page {page_index} to {output_file}")

        return output_file
    except Exception as e:
        logger.error(f"Error rendering page {page_index}: {e}")
        return None


def render_pages(pdf_path: Path, manifest: dict[str, Any], output_dir: Path) -> dict[int, Path]:
    """Render all scan/mixed pages according to manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    poppler_path = settings.poppler_bin if settings.poppler_bin and settings.poppler_bin.exists() else None

    rendered_pages: dict[int, Path] = {}

    pages = manifest.get("pages", [])
    for page_data in pages:
        page_index = page_data["page_index"]
        mode = page_data.get("mode", "native")
        recommended_dpi = page_data.get("recommended_dpi", 0)

        # Render scan and mixed pages
        if mode in ("scan", "mixed") and recommended_dpi > 0:
            try:
                # V6: Use OCR_RENDER_DPI if set (higher quality for OCR)
                render_dpi = max(recommended_dpi, settings.ocr_render_dpi)
                output_file = render_page(pdf_path, page_index, render_dpi, output_dir, poppler_path)
                if output_file:
                    rendered_pages[page_index] = output_file
            except Exception as e:
                logger.error(f"Error rendering page {page_index}: {e}")

    logger.info(f"Rendered {len(rendered_pages)} pages")
    return rendered_pages


if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python step_20_render_pages.py <pdf_path> <manifest_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    output_dir = Path("data/10_work/pages_png")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    render_pages(pdf_path, manifest, output_dir)
