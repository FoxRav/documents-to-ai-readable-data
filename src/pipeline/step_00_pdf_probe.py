"""Step 00: PDF Probe & Route (page classification and manifest generation)."""

import json
import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pdfplumber

from src.pipeline.config import get_settings

logger = logging.getLogger(__name__)


def check_cuda_available() -> dict[str, Any]:
    """Check CUDA availability and GPU info."""
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        else:
            gpu_name = None
            vram_gb = None
        return {
            "cuda_available": cuda_available,
            "gpu_name": gpu_name,
            "vram_gb": vram_gb,
        }
    except ImportError:
        return {"cuda_available": False, "gpu_name": None, "vram_gb": None}


def extract_native_text(page: fitz.Page) -> tuple[int, int]:
    """Extract native text and count characters and blocks."""
    try:
        text = page.get_text()
        text_chars = len(text)
        text_blocks = page.get_text("blocks")
        text_blocks_count = len([b for b in text_blocks if b[6] == 0])  # type 0 = text
        return text_chars, text_blocks_count
    except Exception as e:
        logger.warning(f"Error extracting native text: {e}")
        return 0, 0


def calculate_image_coverage(page: fitz.Page) -> float:
    """Calculate image coverage ratio (image area / page area)."""
    try:
        page_rect = page.rect
        page_area = page_rect.width * page_rect.height

        images = page.get_images(full=True)
        total_image_area = 0.0

        for img_index, img in enumerate(images):
            try:
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                # Get image dimensions
                pix = fitz.Pixmap(page.parent, xref)
                img_area = pix.width * pix.height
                total_image_area += img_area
                pix = None
            except Exception as e:
                logger.debug(f"Error processing image {img_index}: {e}")
                continue

        if page_area > 0:
            coverage = total_image_area / page_area
            return min(coverage, 1.0)  # Cap at 1.0
        return 0.0
    except Exception as e:
        logger.warning(f"Error calculating image coverage: {e}")
        return 0.0


def calculate_vector_line_density(page: fitz.Page) -> float:
    """Calculate vector line density (heuristic for table detection)."""
    try:
        drawings = page.get_drawings()
        if not drawings:
            return 0.0

        total_line_length = 0.0
        line_count = 0

        for drawing in drawings:
            if "items" in drawing:
                for item in drawing["items"]:
                    if item[0] == "l":  # line
                        p1, p2 = item[1], item[2]
                        length = ((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2) ** 0.5
                        total_line_length += length
                        line_count += 1

        page_rect = page.rect
        page_area = page_rect.width * page_rect.height

        if page_area > 0:
            # Normalize by page area (heuristic density)
            density = (total_line_length / page_area) * 1000  # Scale factor
            return min(density, 1.0)  # Cap at 1.0
        return 0.0
    except Exception as e:
        logger.warning(f"Error calculating vector line density: {e}")
        return 0.0


def classify_page(
    native_text_chars: int,
    image_coverage_ratio: float,
    vector_line_density: float,
) -> tuple[str, int, str]:
    """
    Classify page mode and determine recommended DPI and device.

    Returns:
        (mode, recommended_dpi, recommended_device)
    """
    # Classification rules (v1)
    if native_text_chars >= 300 and image_coverage_ratio < 0.40:
        mode = "native"
        recommended_dpi = 0  # No rendering needed by default
        recommended_device = "cpu"
    elif native_text_chars < 50 and image_coverage_ratio >= 0.60:
        mode = "scan"
        # 300 DPI if high line density (table suspicion), else 200-250
        recommended_dpi = 300 if vector_line_density > 0.3 else 250
        recommended_device = "cuda" if check_cuda_available()["cuda_available"] else "cpu"
    else:
        mode = "mixed"
        recommended_dpi = 300 if vector_line_density > 0.3 else 250
        recommended_device = "cuda" if check_cuda_available()["cuda_available"] else "cpu"

    return mode, recommended_dpi, recommended_device


def probe_pdf(pdf_path: Path, output_dir: Path, max_pages: int | None = None) -> dict[str, Any]:
    """Probe PDF and generate page manifest."""
    logger.info(f"Probing PDF: {pdf_path}")

    device_profile = check_cuda_available()

    # Open PDF with PyMuPDF
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    # Limit pages if max_pages is set
    pages_to_process = total_pages
    if max_pages is not None:
        pages_to_process = min(max_pages, total_pages)
        logger.info(f"PDF has {total_pages} pages, processing first {pages_to_process} pages")
    else:
        logger.info(f"PDF has {total_pages} pages")

    pages_data: list[dict[str, Any]] = []

    for page_index in range(pages_to_process):
        page = doc[page_index]
        page_rect = page.rect

        # Extract signals
        native_text_chars, text_blocks_count = extract_native_text(page)
        image_coverage_ratio = calculate_image_coverage(page)
        vector_line_density = calculate_vector_line_density(page)

        # Classify
        mode, recommended_dpi, recommended_device = classify_page(
            native_text_chars, image_coverage_ratio, vector_line_density
        )

        # Build notes
        notes: list[str] = []
        if native_text_chars >= 300:
            notes.append("text_ok")
        if image_coverage_ratio > 0.60:
            notes.append("scan_like")
        if vector_line_density > 0.3:
            notes.append("table_suspicion")

        page_data = {
            "page_index": page_index,
            "width": page_rect.width,
            "height": page_rect.height,
            "native_text_chars": native_text_chars,
            "text_blocks_count": text_blocks_count,
            "image_coverage_ratio": round(image_coverage_ratio, 3),
            "vector_line_density": round(vector_line_density, 3),
            "mode": mode,
            "recommended_dpi": recommended_dpi,
            "recommended_device": recommended_device,
            "notes": notes,
        }

        pages_data.append(page_data)
        logger.debug(f"Page {page_index}: mode={mode}, dpi={recommended_dpi}, device={recommended_device}")

    doc.close()

    # Estimate cost (rough: render_dpi * pages)
    estimated_cost = sum(p.get("recommended_dpi", 0) * 1 for p in pages_data)

    manifest = {
        "device_profile": device_profile,
        "pdf": {
            "filename": pdf_path.name,
            "pages": pages_to_process,  # Use processed pages count
            "total_pages": total_pages,  # Keep original total for reference
        },
        "pages": pages_data,
        "estimated_cost": estimated_cost,
    }

    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info(f"Manifest saved to {manifest_path}")
    logger.info(f"Page classification summary: {sum(1 for p in pages_data if p['mode'] == 'native')} native, "
                f"{sum(1 for p in pages_data if p['mode'] == 'scan')} scan, "
                f"{sum(1 for p in pages_data if p['mode'] == 'mixed')} mixed")

    return manifest


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python step_00_pdf_probe.py <pdf_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    output_dir = Path("data/10_work/page_manifest")
    output_dir.mkdir(parents=True, exist_ok=True)

    probe_pdf(pdf_path, output_dir)
