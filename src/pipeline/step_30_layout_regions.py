"""Step 30: Layout region detection (table, text, figure, header, footer)."""

import json
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Try to use OpenCV with CUDA if available
try:
    if cv2.cuda.getCudaEnabledDeviceCount() > 0:
        logger.info(f"OpenCV CUDA available: {cv2.cuda.getCudaEnabledDeviceCount()} device(s)")
        USE_CUDA = True
    else:
        USE_CUDA = False
except Exception:
    USE_CUDA = False


def detect_table_regions(image_path: Path) -> list[dict[str, Any]]:
    """Detect table regions using OpenCV line detection."""
    try:
        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            logger.warning(f"Could not load image: {image_path}")
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        detected_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        horizontal_lines = cv2.HoughLinesP(
            detected_lines, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
        )

        # Detect vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        detected_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        vertical_lines = cv2.HoughLinesP(
            detected_lines, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
        )

        # Find intersections to identify table regions
        regions: list[dict[str, Any]] = []

        if horizontal_lines is not None and vertical_lines is not None:
            # Simple heuristic: if we have both horizontal and vertical lines, it's likely a table
            # Group lines to find bounding boxes
            h_points = []
            v_points = []

            for line in horizontal_lines:
                x1, y1, x2, y2 = line[0]
                h_points.extend([(x1, y1), (x2, y2)])

            for line in vertical_lines:
                x1, y1, x2, y2 = line[0]
                v_points.extend([(x1, y1), (x2, y2)])

            if h_points and v_points:
                # Find bounding box of all line points
                all_points = h_points + v_points
                x_coords = [p[0] for p in all_points]
                y_coords = [p[1] for p in all_points]

                if x_coords and y_coords:
                    x0 = min(x_coords)
                    y0 = min(y_coords)
                    x1 = max(x_coords)
                    y1 = max(y_coords)

                    # Only add if region is large enough
                    if (x1 - x0) > 100 and (y1 - y0) > 100:
                        regions.append(
                            {
                                "type": "table",
                                "bbox": {"x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1)},
                                "confidence": 0.7,  # Heuristic confidence
                            }
                        )

        # If no table regions found, try simpler approach: detect rectangular regions
        if not regions:
            # Use contour detection
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 10000:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    # Check aspect ratio (tables are usually wider than tall)
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.5 < aspect_ratio < 3.0:  # Reasonable table aspect ratio
                        regions.append(
                            {
                                "type": "table",
                                "bbox": {"x0": float(x), "y0": float(y), "x1": float(x + w), "y1": float(y + h)},
                                "confidence": 0.5,
                            }
                        )

        return regions
    except Exception as e:
        logger.error(f"Error detecting table regions in {image_path}: {e}")
        return []


def detect_text_regions(image_path: Path, table_regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect text regions (excluding table regions)."""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return []

        height, width = img.shape[:2]

        # Simple heuristic: divide page into regions, exclude table areas
        regions: list[dict[str, Any]] = []

        # Divide into top, middle, bottom sections
        section_height = height // 3

        for i in range(3):
            y0 = i * section_height
            y1 = (i + 1) * section_height if i < 2 else height

            # Check if this section overlaps with table regions
            overlaps_table = False
            for table_region in table_regions:
                t_bbox = table_region["bbox"]
                if not (y1 < t_bbox["y0"] or y0 > t_bbox["y1"]):
                    overlaps_table = True
                    break

            if not overlaps_table:
                regions.append(
                    {
                        "type": "text",
                        "bbox": {"x0": 0.0, "y0": float(y0), "x1": float(width), "y1": float(y1)},
                        "confidence": 0.6,
                    }
                )

        return regions
    except Exception as e:
        logger.error(f"Error detecting text regions in {image_path}: {e}")
        return []


def detect_regions(image_path: Path) -> list[dict[str, Any]]:
    """Detect all layout regions."""
    table_regions = detect_table_regions(image_path)
    text_regions = detect_text_regions(image_path, table_regions)

    all_regions = table_regions + text_regions

    # Sort by y-coordinate (top to bottom)
    all_regions.sort(key=lambda r: r["bbox"]["y0"])

    return all_regions


def process_rendered_pages(
    rendered_pages: dict[int, Path], output_dir: Path
) -> dict[int, list[dict[str, Any]]]:
    """Process all rendered pages and detect regions."""
    output_dir.mkdir(parents=True, exist_ok=True)

    all_regions: dict[int, list[dict[str, Any]]] = {}

    # Process pages in parallel for better performance
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from src.pipeline.config import get_settings

    settings = get_settings()
    max_workers = min(settings.cpu_concurrency, len(rendered_pages))

    def process_page(page_index: int, image_path: Path) -> tuple[int, list[dict[str, Any]]]:
        """Process a single page."""
        try:
            regions = detect_regions(image_path)
            
            # Save regions JSON
            output_file = output_dir / f"page_{page_index:04d}_regions.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(regions, f, indent=2, ensure_ascii=False)

            logger.info(f"Detected {len(regions)} regions on page {page_index}")
            return page_index, regions
        except Exception as e:
            logger.error(f"Error processing page {page_index}: {e}")
            return page_index, []

    # Process pages in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_page, page_index, image_path): page_index
            for page_index, image_path in rendered_pages.items()
        }

        for future in as_completed(futures):
            page_index, regions = future.result()
            all_regions[page_index] = regions

    return all_regions

    return all_regions


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python step_30_layout_regions.py <image_path>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    output_dir = Path("data/10_work/regions")

    regions = detect_regions(image_path)
    print(json.dumps(regions, indent=2))
