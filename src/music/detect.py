"""Music sheet detection using computer vision."""

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def detect_staff_lines(image: np.ndarray) -> list[dict[str, Any]]:
    """
    Detect horizontal staff lines in an image.
    
    Staff lines are characterized by:
    - Long horizontal lines
    - Groups of 5 parallel lines (standard music staff)
    - Relatively uniform spacing
    
    Args:
        image: Input image (BGR or grayscale)
    
    Returns:
        List of detected staff line groups with positions
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Binarize
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Detect horizontal lines using morphology
    # Staff lines are thin and long
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    
    # Find contours of horizontal lines
    contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter and sort by y-coordinate
    lines: list[dict[str, Any]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Staff lines should be wide (at least 30% of image width) and thin
        if w > image.shape[1] * 0.3 and h < 10:
            lines.append({
                "y": y,
                "x": x,
                "width": w,
                "height": h,
            })
    
    # Sort by y-coordinate
    lines.sort(key=lambda l: l["y"])
    
    # Group lines into staves (groups of 5)
    staves: list[dict[str, Any]] = []
    if len(lines) >= 5:
        # Simple grouping: consecutive lines with similar spacing
        i = 0
        while i <= len(lines) - 5:
            group = lines[i:i+5]
            # Check if spacing is relatively uniform
            spacings = [group[j+1]["y"] - group[j]["y"] for j in range(4)]
            avg_spacing = sum(spacings) / 4
            
            # If spacing variation is small, it's likely a staff
            if all(abs(s - avg_spacing) < avg_spacing * 0.3 for s in spacings):
                staves.append({
                    "staff_index": len(staves),
                    "top_y": group[0]["y"],
                    "bottom_y": group[4]["y"],
                    "line_spacing": avg_spacing,
                    "lines": group,
                })
                i += 5
            else:
                i += 1
    
    logger.debug(f"Detected {len(staves)} music staves from {len(lines)} lines")
    return staves


def is_music_sheet(image: np.ndarray, min_staves: int = 3) -> tuple[bool, float, dict[str, Any]]:
    """
    Detect if an image is a music sheet.
    
    Heuristics:
    - Multiple parallel horizontal staff lines (groups of 5)
    - At least N staff systems (default 3)
    - Staff lines span significant width of page
    
    Args:
        image: Input image (BGR or grayscale)
        min_staves: Minimum number of staff systems to qualify as music sheet
    
    Returns:
        Tuple of (is_music, confidence, detection_info)
    """
    staves = detect_staff_lines(image)
    
    detection_info = {
        "staff_count": len(staves),
        "min_staves_required": min_staves,
        "staves": staves,
    }
    
    if len(staves) >= min_staves:
        # Calculate confidence based on staff count and quality
        # More staves = higher confidence
        confidence = min(0.5 + (len(staves) / 20), 0.95)
        return True, confidence, detection_info
    
    return False, 0.0, detection_info


def detect_music_sheet_from_path(image_path: Path | str) -> tuple[bool, float, dict[str, Any]]:
    """
    Detect if an image file is a music sheet.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Tuple of (is_music, confidence, detection_info)
    """
    image = cv2.imread(str(image_path))
    if image is None:
        logger.error(f"Could not read image: {image_path}")
        return False, 0.0, {"error": "Could not read image"}
    
    return is_music_sheet(image)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) < 2:
        print("Usage: python detect.py <image_path>")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    is_music, confidence, info = detect_music_sheet_from_path(image_path)
    
    print(f"Is music sheet: {is_music}")
    print(f"Confidence: {confidence:.2f}")
    print(f"Staff count: {info.get('staff_count', 0)}")
