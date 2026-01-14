"""
OMR Preflight 2: Structural Anchoring.

Detects and assigns time signature, clef, and key signature hints
to improve Audiveris rhythm inference.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Common time signatures
TIME_SIG_PATTERNS = [
    r"(\d+)/(\d+)",  # 4/4, 6/8, etc.
    r"[Cc]",  # Common time (C)
    r"[Cc]\|",  # Cut time (C|)
]

# Clef symbols (simplified detection)
CLEF_PATTERNS = {
    "G": ["treble", "violin", "G-clef"],
    "F": ["bass", "F-clef"],
    "C": ["alto", "tenor", "C-clef"],
}


@dataclass
class StructuralHints:
    """Structural hints for Audiveris."""
    
    time_signature: str | None = None  # e.g., "4/4", "6/8", "C"
    clef: str | None = None  # "G", "F", "C"
    key_signature: str | None = None  # "C", "G", "F", "F#m", etc.
    default_time_sig: str = "4/4"  # Fallback if not detected


def detect_time_signature_hint(
    image: np.ndarray,
    header_region: np.ndarray | None,
    text_blocks: list[dict[str, Any]],
) -> str | None:
    """
    Detect time signature from header region or text blocks.
    
    Args:
        image: Full image
        header_region: Header region image (if available)
        text_blocks: OCR text blocks from header
    
    Returns:
        Time signature string (e.g., "4/4", "6/8") or None
    """
    # Method 1: Check text blocks for time signature patterns
    for block in text_blocks:
        if block.get("region") != "header":
            continue
        
        text = block.get("text", "").strip()
        
        # Check for numeric time signatures
        match = re.search(r"(\d+)/(\d+)", text)
        if match:
            num, denom = match.groups()
            # Validate: denominator should be power of 2
            if denom in ["2", "4", "8", "16"]:
                time_sig = f"{num}/{denom}"
                logger.info(f"Detected time signature from text: {time_sig}")
                return time_sig
        
        # Check for common time (C)
        if text.upper() in ["C", "COMMON TIME"]:
            logger.info("Detected common time (C) from text")
            return "4/4"  # Common time = 4/4
    
    # Method 2: Symbol detection in header region (if available)
    if header_region is not None:
        # Look for time signature symbols (simplified)
        # This would require more sophisticated symbol recognition
        # For now, return None if text detection fails
        pass
    
    return None


def detect_clef_hint(
    image: np.ndarray,
    first_staff_region: np.ndarray | None,
    staves: list[dict[str, Any]],
) -> str | None:
    """
    Detect clef from first staff system.
    
    Args:
        image: Full image
        first_staff_region: First staff region image (if available)
        staves: Detected staff systems
    
    Returns:
        Clef string ("G", "F", "C") or None
    """
    if not staves:
        return None
    
    # Extract first staff region
    first_staff = staves[0]
    top_y = first_staff["top_y"]
    bottom_y = first_staff["bottom_y"]
    
    # Get left portion of first staff (where clef typically appears)
    staff_height = bottom_y - top_y
    left_margin = int(image.shape[1] * 0.05)  # 5% from left
    clef_width = int(image.shape[1] * 0.15)  # 15% width for clef area
    
    clef_region = image[
        max(0, top_y - staff_height):min(image.shape[0], bottom_y + staff_height),
        left_margin:min(image.shape[1], left_margin + clef_width)
    ]
    
    if clef_region.size == 0:
        return None
    
    # Simplified clef detection using pattern matching
    # G-clef: typically has characteristic shape in upper staff
    # F-clef: typically in lower staff
    # For now, use heuristics based on staff position
    
    # If first staff is in upper half of image → likely treble (G)
    if top_y < image.shape[0] * 0.5:
        logger.info("Detected G-clef (treble) by position")
        return "G"
    
    # If first staff is in lower half → could be bass (F)
    # But default to G for most music
    logger.info("Defaulting to G-clef (treble)")
    return "G"


def smooth_key_signature(measures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Propagate first valid key signature to all measures.
    
    Args:
        measures: List of measure dicts (from OMR parsing)
    
    Returns:
        Measures with key signatures smoothed
    """
    if not measures:
        return measures
    
    # Find first valid key signature
    first_key: str | None = None
    for measure in measures:
        key = measure.get("key_signature")
        if key and key != "C":  # Skip default C
            first_key = key
            break
    
    # If no key found, try to find any key (even C)
    if not first_key:
        for measure in measures:
            key = measure.get("key_signature")
            if key:
                first_key = key
                break
    
    # Propagate to all measures
    if first_key:
        for measure in measures:
            if not measure.get("key_signature"):
                measure["key_signature"] = first_key
                logger.debug(f"Propagated key {first_key} to measure {measure.get('number')}")
    
    return measures


def run_preflight2(
    image: np.ndarray,
    staves: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
    measures: list[dict[str, Any]] | None = None,
) -> StructuralHints:
    """
    Run Preflight 2: Detect structural hints.
    
    Args:
        image: Input image
        staves: Detected staff systems
        text_blocks: OCR text blocks
        measures: Parsed measures (for key smoothing)
    
    Returns:
        StructuralHints with detected/assigned values
    """
    hints = StructuralHints()
    
    # Extract header region for time signature detection
    header_region: np.ndarray | None = None
    if staves:
        header_bottom = staves[0]["top_y"] - 20
        if header_bottom > 0:
            header_region = image[0:max(10, header_bottom), :]
    
    # Detect time signature
    time_sig = detect_time_signature_hint(image, header_region, text_blocks)
    if time_sig:
        hints.time_signature = time_sig
    else:
        hints.time_signature = hints.default_time_sig
        logger.info(f"No time signature detected, using default: {hints.default_time_sig}")
    
    # Detect clef
    clef = detect_clef_hint(image, None, staves)
    if clef:
        hints.clef = clef
    else:
        hints.clef = "G"  # Default to treble
        logger.info("No clef detected, using default: G (treble)")
    
    # Smooth key signature (if measures available)
    if measures:
        measures = smooth_key_signature(measures)
        # Extract first key from smoothed measures
        for m in measures:
            if m.get("key_signature"):
                hints.key_signature = m["key_signature"]
                break
    
    return hints


def hints_to_dict(hints: StructuralHints) -> dict[str, Any]:
    """Convert StructuralHints to JSON-serializable dict."""
    return {
        "time_signature": hints.time_signature,
        "clef": hints.clef,
        "key_signature": hints.key_signature,
        "default_time_sig": hints.default_time_sig,
    }
