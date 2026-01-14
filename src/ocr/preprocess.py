"""OCR image preprocessing for better Tesseract results (V6/V8)."""

import cv2
import numpy as np
from pathlib import Path
from typing import Literal

import logging

logger = logging.getLogger(__name__)

# Preprocessing modes
PreprocessMode = Literal["standard", "aggressive", "minimal"]


def preprocess_for_ocr(
    image_path: Path | str,
    output_path: Path | None = None,
    mode: PreprocessMode = "standard",
) -> np.ndarray:
    """
    Preprocess image for OCR to reduce noise and improve quality.
    
    Modes:
    - "standard": Balanced preprocessing (default)
    - "aggressive": Heavy noise removal for bad OCR pages (V8)
    - "minimal": Light preprocessing, preserves more detail
    
    Args:
        image_path: Path to input image
        output_path: Optional path to save preprocessed image
        mode: Preprocessing mode
        
    Returns:
        Preprocessed image as numpy array
    """
    # Read image
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Step 1: Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    
    # V8: Mode-specific preprocessing
    if mode == "minimal":
        # Minimal: just grayscale + light contrast enhancement
        result = cv2.equalizeHist(gray)
        
    elif mode == "aggressive":
        # V8 Aggressive: heavy noise removal for bad OCR pages
        logger.debug("Using aggressive preprocessing for bad OCR page")
        
        # Step 2a: Increase contrast with CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Step 2b: Bilateral filter (edge-preserving smoothing)
        smoothed = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # Step 2c: Otsu's threshold (works well for scanned documents)
        _, binary = cv2.threshold(smoothed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Step 2d: Morphological operations to clean up
        # Opening (erosion + dilation) removes small noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # Closing (dilation + erosion) fills small holes
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        
        # Step 2e: Heavy denoising
        denoised = cv2.fastNlMeansDenoising(
            closed,
            None,
            h=20,  # Higher filter strength
            templateWindowSize=7,
            searchWindowSize=21,
        )
        
        # Step 2f: Deskew
        angle = detect_skew_angle(denoised)
        if abs(angle) > 0.3:  # More sensitive angle threshold
            logger.debug(f"Detected skew angle: {angle:.2f} degrees, correcting...")
            result = rotate_image(denoised, angle)
        else:
            result = denoised
            
    else:
        # Standard mode (original V6 logic)
        # Step 2: Adaptive threshold
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,  # block size
            2,   # C constant
        )
        
        # Step 3: Denoise (light)
        denoised = cv2.fastNlMeansDenoising(
            binary,
            None,
            h=10,  # Filter strength
            templateWindowSize=7,
            searchWindowSize=21,
        )
        
        # Step 4: Deskew
        angle = detect_skew_angle(denoised)
        if abs(angle) > 0.5:
            logger.debug(f"Detected skew angle: {angle:.2f} degrees, correcting...")
            result = rotate_image(denoised, angle)
        else:
            result = denoised
    
    # Save if output path provided
    if output_path:
        cv2.imwrite(str(output_path), result)
        logger.debug(f"Saved preprocessed image to: {output_path}")
    
    return result


def detect_skew_angle(image: np.ndarray) -> float:
    """
    Detect skew angle in image using Hough line transform.
    
    Args:
        image: Binary image
        
    Returns:
        Skew angle in degrees
    """
    # Use edge detection
    edges = cv2.Canny(image, 50, 150, apertureSize=3)
    
    # Hough line transform
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is None or len(lines) == 0:
        return 0.0
    
    # Calculate angles
    angles = []
    for line in lines[:20]:  # Use first 20 lines
        rho, theta = line[0]
        angle = np.degrees(theta) - 90
        # Normalize to -45 to 45 degrees
        if angle > 45:
            angle -= 90
        elif angle < -45:
            angle += 90
        angles.append(angle)
    
    # Return median angle
    if angles:
        return float(np.median(angles))
    return 0.0


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """
    Rotate image to correct skew.
    
    Args:
        image: Input image
        angle: Rotation angle in degrees
        
    Returns:
        Rotated image
    """
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    
    # Get rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Rotate
    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    
    return rotated


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) < 2:
        print("Usage: python preprocess.py <image_path> [output_path]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    preprocessed = preprocess_for_ocr(input_path, output_path)
    print(f"Preprocessed image shape: {preprocessed.shape}")
