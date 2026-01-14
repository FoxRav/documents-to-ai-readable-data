"""OCR smoke test - test PaddleOCR and pytesseract with a single rendered page (V6: with quality metrics)."""

import logging
import re
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_paddleocr_cpu(image_path: Path) -> int:
    """Test PaddleOCR in CPU mode."""
    try:
        from paddleocr import PaddleOCR

        logger.info("Testing PaddleOCR CPU mode...")
        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False, use_gpu=False)
        
        img = cv2.imread(str(image_path))
        if img is None:
            logger.error(f"Could not read image: {image_path}")
            return 0
        
        result = ocr.ocr(img, cls=True)
        
        blocks_count = 0
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    blocks_count += 1
                    text = line[1][0]
                    logger.debug(f"Found text: {text[:50]}...")
        
        logger.info(f"PaddleOCR CPU: {blocks_count} blocks found")
        return blocks_count
    except Exception as e:
        logger.error(f"PaddleOCR CPU failed: {e}")
        return 0


def test_paddleocr_gpu(image_path: Path) -> int:
    """Test PaddleOCR in GPU mode."""
    try:
        from paddleocr import PaddleOCR
        import torch

        if not torch.cuda.is_available():
            logger.warning("CUDA not available, skipping GPU test")
            return 0

        logger.info("Testing PaddleOCR GPU mode...")
        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False, use_gpu=True)
        
        img = cv2.imread(str(image_path))
        if img is None:
            logger.error(f"Could not read image: {image_path}")
            return 0
        
        result = ocr.ocr(img, cls=True)
        
        blocks_count = 0
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    blocks_count += 1
                    text = line[1][0]
                    logger.debug(f"Found text: {text[:50]}...")
        
        logger.info(f"PaddleOCR GPU: {blocks_count} blocks found")
        return blocks_count
    except Exception as e:
        logger.error(f"PaddleOCR GPU failed: {e}")
        return 0


def analyze_text_quality(text: str) -> dict[str, float | list[str]]:
    """
    Analyze OCR text quality (V6).
    
    Returns:
        - avg_char_density: Average characters per word
        - non_alpha_ratio: Ratio of non-alphabetic characters
        - top_trigrams: Top 10 trigrams (to detect noise like "eee/ccc")
    """
    if not text or not text.strip():
        return {
            "avg_char_density": 0.0,
            "non_alpha_ratio": 0.0,
            "top_trigrams": [],
        }
    
    # Remove whitespace for analysis
    text_clean = text.replace(" ", "").replace("\n", "")
    
    # Calculate character density (chars per "word" - split by common separators)
    words = re.findall(r"\w+", text)
    if words:
        avg_char_density = sum(len(w) for w in words) / len(words)
    else:
        avg_char_density = 0.0
    
    # Calculate non-alphabetic character ratio
    total_chars = len(text_clean)
    alpha_chars = sum(1 for c in text_clean if c.isalpha())
    non_alpha_ratio = (total_chars - alpha_chars) / total_chars if total_chars > 0 else 0.0
    
    # Extract trigrams (3-character sequences)
    trigrams = []
    for i in range(len(text_clean) - 2):
        trigram = text_clean[i:i+3].lower()
        if all(c.isalnum() for c in trigram):  # Only alphanumeric trigrams
            trigrams.append(trigram)
    
    # Count trigrams and get top 10
    trigram_counts = Counter(trigrams)
    top_trigrams = [f"{trigram}:{count}" for trigram, count in trigram_counts.most_common(10)]
    
    return {
        "avg_char_density": round(avg_char_density, 2),
        "non_alpha_ratio": round(non_alpha_ratio, 3),
        "top_trigrams": top_trigrams,
    }


def test_pytesseract(image_path: Path, use_preprocessing: bool = True) -> tuple[int, dict[str, float | list[str]]]:
    """
    Test pytesseract (V6: with preprocessing and quality metrics).
    
    Returns:
        Tuple of (blocks_count, quality_metrics)
    """
    try:
        import pytesseract
        from PIL import Image
        from src.pipeline.config import get_settings
        from src.ocr.preprocess import preprocess_for_ocr

        logger.info("Testing pytesseract...")
        
        settings = get_settings()
        
        # Configure pytesseract path if set
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = str(settings.tesseract_cmd)
        
        img = cv2.imread(str(image_path))
        if img is None:
            logger.error(f"Could not read image: {image_path}")
            return 0, {}
        
        # V6: Preprocess image if enabled
        if use_preprocessing:
            try:
                preprocessed = preprocess_for_ocr(image_path)
                pil_image = Image.fromarray(preprocessed)
                logger.debug("Applied preprocessing for OCR")
            except Exception as e:
                logger.warning(f"Preprocessing failed, using original image: {e}")
                pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # V6: Use Tesseract settings from config
        tess_config = f"--psm {settings.tess_psm} --oem {settings.tess_oem}"
        
        # Use configured language(s)
        try:
            text = pytesseract.image_to_string(
                pil_image,
                lang=settings.tess_lang,
                config=tess_config,
            )
        except Exception:
            text = pytesseract.image_to_string(
                pil_image,
                lang="eng",
                config=tess_config,
            )
        
        # Count non-empty lines
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        blocks_count = len(lines)
        
        # V6: Analyze text quality
        quality_metrics = analyze_text_quality(text)
        
        logger.info(f"pytesseract: {blocks_count} blocks found")
        if blocks_count > 0:
            logger.debug(f"Sample text: {lines[0][:50]}...")
            logger.info(f"Quality metrics:")
            logger.info(f"  Avg char density: {quality_metrics['avg_char_density']}")
            logger.info(f"  Non-alpha ratio: {quality_metrics['non_alpha_ratio']}")
            logger.info(f"  Top trigrams: {quality_metrics['top_trigrams'][:5]}")
        
        return blocks_count, quality_metrics
    except Exception as e:
        logger.error(f"pytesseract failed: {e}")
        return 0, {}


def main() -> None:
    """Run OCR smoke tests."""
    if len(sys.argv) < 2:
        print("Usage: python ocr_smoke_test.py <image_path>")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        sys.exit(1)
    
    logger.info(f"Testing OCR with image: {image_path}")
    
    # Test PaddleOCR CPU
    cpu_blocks = test_paddleocr_cpu(image_path)
    
    # Test PaddleOCR GPU (if available)
    gpu_blocks = test_paddleocr_gpu(image_path)
    
    # Test pytesseract (V6: with preprocessing and quality metrics)
    tesseract_blocks, quality_metrics = test_pytesseract(image_path, use_preprocessing=True)
    
    # Summary
    logger.info("=" * 60)
    logger.info("OCR Smoke Test Results:")
    logger.info(f"  PaddleOCR CPU: {cpu_blocks} blocks")
    logger.info(f"  PaddleOCR GPU: {gpu_blocks} blocks")
    logger.info(f"  pytesseract:   {tesseract_blocks} blocks")
    logger.info("")
    logger.info("V6 Quality Metrics (Tesseract):")
    if quality_metrics:
        logger.info(f"  Avg char density: {quality_metrics.get('avg_char_density', 0)}")
        logger.info(f"  Non-alpha ratio: {quality_metrics.get('non_alpha_ratio', 0)}")
        logger.info(f"  Top trigrams: {quality_metrics.get('top_trigrams', [])[:5]}")
    logger.info("=" * 60)
    
    if cpu_blocks > 0 or gpu_blocks > 0 or tesseract_blocks > 0:
        logger.info("✅ At least one OCR method works!")
        sys.exit(0)
    else:
        logger.error("❌ All OCR methods failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
