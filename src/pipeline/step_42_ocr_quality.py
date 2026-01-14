"""Step 42: OCR quality metrics and noise gate (V7 Gate A)."""

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def calculate_ocr_quality_metrics(text: str) -> dict[str, Any]:
    """
    Calculate OCR quality metrics for a page (V7).
    
    Returns:
        Dictionary with quality metrics:
        - alpha_ratio: Ratio of alphabetic characters
        - digit_ratio: Ratio of digit characters
        - repeat_run_max: Longest sequence of same character
        - junk_token_ratio: Ratio of junk tokens (1-3 chars, not words)
        - avg_word_len: Average word length
    """
    if not text or not text.strip():
        return {
            "alpha_ratio": 0.0,
            "digit_ratio": 0.0,
            "repeat_run_max": 0,
            "junk_token_ratio": 0.0,
            "avg_word_len": 0.0,
            "status": "empty",
            "score": 0.0,
        }
    
    # Remove whitespace for character analysis
    text_chars = text.replace(" ", "").replace("\n", "")
    total_chars = len(text_chars)
    
    if total_chars == 0:
        return {
            "alpha_ratio": 0.0,
            "digit_ratio": 0.0,
            "repeat_run_max": 0,
            "junk_token_ratio": 0.0,
            "avg_word_len": 0.0,
            "status": "empty",
            "score": 0.0,
        }
    
    # Calculate character ratios
    alpha_chars = sum(1 for c in text_chars if c.isalpha())
    digit_chars = sum(1 for c in text_chars if c.isdigit())
    alpha_ratio = alpha_chars / total_chars
    digit_ratio = digit_chars / total_chars
    
    # Find longest repeat run (e.g., "eeeeeeee")
    repeat_run_max = 0
    if text_chars:
        current_char = text_chars[0]
        current_run = 1
        for char in text_chars[1:]:
            if char == current_char:
                current_run += 1
            else:
                repeat_run_max = max(repeat_run_max, current_run)
                current_char = char
                current_run = 1
        repeat_run_max = max(repeat_run_max, current_run)
    
    # Tokenize and analyze words
    tokens = re.findall(r"\S+", text.lower())
    words = [t for t in tokens if re.match(r"^[a-zäöå]+", t)]  # Only alphabetic words
    
    # Calculate average word length
    if words:
        avg_word_len = sum(len(w) for w in words) / len(words)
    else:
        avg_word_len = 0.0
    
    # Junk tokens: 1-3 chars, not alphabetic words, not numbers
    junk_tokens = []
    for token in tokens:
        if 1 <= len(token) <= 3:
            if not re.match(r"^[a-zäöå]+$", token) and not re.match(r"^\d+$", token):
                junk_tokens.append(token)
    
    junk_token_ratio = len(junk_tokens) / len(tokens) if tokens else 0.0
    
    # Calculate quality score (0-1, higher is better)
    score = (
        alpha_ratio * 0.4
        + (1.0 - min(junk_token_ratio, 1.0)) * 0.3
        + (1.0 - min(repeat_run_max / 20.0, 1.0)) * 0.2
        + min(avg_word_len / 10.0, 1.0) * 0.1
    )
    
    # Determine status
    if repeat_run_max >= 10 or (alpha_ratio < 0.30 and digit_ratio < 0.05):
        status = "bad"
    elif score < 0.5:
        status = "poor"
    elif score < 0.7:
        status = "fair"
    else:
        status = "good"
    
    return {
        "alpha_ratio": round(alpha_ratio, 3),
        "digit_ratio": round(digit_ratio, 3),
        "repeat_run_max": repeat_run_max,
        "junk_token_ratio": round(junk_token_ratio, 3),
        "avg_word_len": round(avg_word_len, 2),
        "status": status,
        "score": round(score, 3),
    }


def apply_noise_gate(quality_metrics: dict[str, Any]) -> bool:
    """
    Apply noise gate rules (V7).
    
    Returns:
        True if page should be rejected (bad quality)
    """
    repeat_run_max = quality_metrics.get("repeat_run_max", 0)
    alpha_ratio = quality_metrics.get("alpha_ratio", 0.0)
    digit_ratio = quality_metrics.get("digit_ratio", 0.0)
    
    # Noise gate rules
    if repeat_run_max >= 10:
        return True
    
    if alpha_ratio < 0.30 and digit_ratio < 0.05:
        return True
    
    return False


def adaptive_psm_pass(
    image_path: Path, text_regions: list[dict[str, Any]], page_index: int, pass_num: int
) -> tuple[str, dict[str, Any]]:
    """
    Run OCR with adaptive PSM (V7).
    
    Pass 1: PSM=6 (uniform block)
    Pass 2: PSM=11 (sparse text)
    Pass 3: PSM=4 (single column)
    
    Returns:
        Tuple of (text, quality_metrics)
    """
    import pytesseract
    from PIL import Image
    import cv2
    from src.pipeline.config import get_settings
    from src.ocr.preprocess import preprocess_for_ocr
    
    settings = get_settings()
    
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = str(settings.tesseract_cmd)
    
    # PSM mapping
    psm_map = {1: 6, 2: 11, 3: 4}
    psm = psm_map.get(pass_num, 6)
    
    # Read and preprocess image
    img = cv2.imread(str(image_path))
    if img is None:
        return "", {}
    
    # Preprocess
    preprocessed = preprocess_for_ocr(image_path)
    pil_image = Image.fromarray(preprocessed)
    
    # OCR with specific PSM
    tess_config = f"--psm {psm} --oem {settings.tess_oem}"
    
    try:
        text = pytesseract.image_to_string(
            pil_image,
            lang=settings.tess_lang,
            config=tess_config,
        )
    except Exception as e:
        logger.warning(f"Pass {pass_num} (PSM={psm}) failed: {e}")
        return "", {}
    
    # Calculate quality metrics
    quality_metrics = calculate_ocr_quality_metrics(text)
    quality_metrics["psm"] = psm
    quality_metrics["pass"] = pass_num
    
    return text, quality_metrics


def process_page_ocr_quality(
    page_index: int, ocr_text: str, debug_dir: Path
) -> dict[str, Any]:
    """
    Process OCR quality for a page (V7 Gate A).
    
    Returns:
        Quality metrics dictionary
    """
    quality_metrics = calculate_ocr_quality_metrics(ocr_text)
    
    # Save to debug directory
    debug_dir.mkdir(parents=True, exist_ok=True)
    quality_file = debug_dir / f"page_{page_index:04d}_ocr_quality.json"
    with open(quality_file, "w", encoding="utf-8") as f:
        json.dump(quality_metrics, f, indent=2, ensure_ascii=False)
    
    logger.debug(
        f"Page {page_index} OCR quality: status={quality_metrics['status']}, "
        f"score={quality_metrics['score']}, repeat_run_max={quality_metrics['repeat_run_max']}"
    )
    
    return quality_metrics


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python step_42_ocr_quality.py <text>")
        sys.exit(1)
    
    text = sys.argv[1]
    metrics = calculate_ocr_quality_metrics(text)
    print(json.dumps(metrics, indent=2))
