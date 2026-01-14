"""
OMR Preflight: Automatic image preprocessing for Audiveris.

Audiveris requires sufficient interline (staff line spacing) in pixels.
If interline is too small (< 12px), the image is automatically upscaled.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Minimum interline for Audiveris (pixels)
MIN_INTERLINE_PX = 12

# Target interline after upscaling (pixels)
TARGET_INTERLINE_PX = 20


@dataclass
class PreflightResult:
    """Result of OMR preflight check."""
    
    needs_upscale: bool
    detected_interline_px: float
    target_interline_px: float
    scale_factor: float
    upscaled_path: Path | None
    original_size: tuple[int, int]  # (width, height)
    upscaled_size: tuple[int, int] | None
    

def get_median_interline(staves: list[dict[str, Any]]) -> float:
    """
    Calculate median interline (line spacing) from detected staves.
    
    Args:
        staves: List of staff dictionaries from detect_staff_lines()
    
    Returns:
        Median interline in pixels, or 0 if no staves
    """
    if not staves:
        return 0.0
    
    spacings = [staff.get("line_spacing", 0) for staff in staves if staff.get("line_spacing")]
    
    if not spacings:
        return 0.0
    
    return float(np.median(spacings))


def calculate_scale_factor(interline_px: float) -> float:
    """
    Calculate upscale factor to achieve target interline.
    
    Args:
        interline_px: Current interline in pixels
    
    Returns:
        Scale factor (1.0 = no change, >1.0 = upscale)
    """
    if interline_px <= 0:
        return 1.0
    
    if interline_px >= MIN_INTERLINE_PX:
        return 1.0
    
    return TARGET_INTERLINE_PX / interline_px


def upscale_image(
    image: np.ndarray,
    scale_factor: float,
    output_path: Path,
) -> tuple[np.ndarray, tuple[int, int]]:
    """
    Upscale image by given factor and save to output path.
    
    Args:
        image: Input image (BGR or grayscale)
        scale_factor: Scale factor (>1.0 for upscale)
        output_path: Path to save upscaled image
    
    Returns:
        Tuple of (upscaled_image, (new_width, new_height))
    """
    if scale_factor <= 1.0:
        return image, (image.shape[1], image.shape[0])
    
    # Calculate new dimensions
    new_width = int(image.shape[1] * scale_factor)
    new_height = int(image.shape[0] * scale_factor)
    
    # Upscale using INTER_CUBIC for quality
    upscaled = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # Save to output path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), upscaled)
    
    logger.info(
        f"Upscaled image: {image.shape[1]}x{image.shape[0]} -> {new_width}x{new_height} "
        f"(scale={scale_factor:.2f})"
    )
    
    return upscaled, (new_width, new_height)


def run_preflight(
    image_path: Path,
    staves: list[dict[str, Any]],
    output_dir: Path,
) -> PreflightResult:
    """
    Run OMR preflight check and upscale if needed.
    
    Args:
        image_path: Path to original image
        staves: Detected staff systems from detect_staff_lines()
        output_dir: Directory for debug/upscaled outputs
    
    Returns:
        PreflightResult with upscale info
    """
    # Load original image
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    original_size = (image.shape[1], image.shape[0])
    
    # Calculate median interline
    detected_interline = get_median_interline(staves)
    
    if detected_interline == 0:
        logger.warning("No interline detected from staves, skipping preflight")
        return PreflightResult(
            needs_upscale=False,
            detected_interline_px=0,
            target_interline_px=TARGET_INTERLINE_PX,
            scale_factor=1.0,
            upscaled_path=None,
            original_size=original_size,
            upscaled_size=None,
        )
    
    # Calculate scale factor
    scale_factor = calculate_scale_factor(detected_interline)
    needs_upscale = scale_factor > 1.0
    
    logger.info(
        f"Preflight: interline={detected_interline:.1f}px, "
        f"min={MIN_INTERLINE_PX}px, needs_upscale={needs_upscale}"
    )
    
    upscaled_path: Path | None = None
    upscaled_size: tuple[int, int] | None = None
    
    if needs_upscale:
        # Create debug directory
        debug_dir = output_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        upscaled_path = debug_dir / "omr_input_upscaled.png"
        _, upscaled_size = upscale_image(image, scale_factor, upscaled_path)
        
        logger.info(f"Saved upscaled image: {upscaled_path}")
    
    return PreflightResult(
        needs_upscale=needs_upscale,
        detected_interline_px=detected_interline,
        target_interline_px=TARGET_INTERLINE_PX,
        scale_factor=scale_factor,
        upscaled_path=upscaled_path,
        original_size=original_size,
        upscaled_size=upscaled_size,
    )


def preflight_to_dict(result: PreflightResult) -> dict[str, Any]:
    """Convert PreflightResult to JSON-serializable dict."""
    return {
        "needs_upscale": result.needs_upscale,
        "detected_interline_px": result.detected_interline_px,
        "target_interline_px": result.target_interline_px,
        "scale_factor": result.scale_factor,
        "upscaled_path": str(result.upscaled_path) if result.upscaled_path else None,
        "original_size": list(result.original_size),
        "upscaled_size": list(result.upscaled_size) if result.upscaled_size else None,
    }
