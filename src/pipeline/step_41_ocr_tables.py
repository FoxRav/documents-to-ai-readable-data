"""Step 41: OCR tables and text regions using PaddleOCR PP-StructureV3 (for scan/mixed pages)."""

import json
import logging
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from src.pipeline.config import get_settings
from src.schemas.models import BBox, Block, Cell, SourceType, Table

logger = logging.getLogger(__name__)

# V4: Initialize settings and configure pytesseract
settings = get_settings()
if settings.tesseract_cmd:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = str(settings.tesseract_cmd)
    logger.info(f"Configured pytesseract to use: {settings.tesseract_cmd}")


def crop_table_region(image_path: Path, bbox: dict[str, float]) -> np.ndarray | None:
    """Crop table region from image."""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return None

        x0 = int(bbox["x0"])
        y0 = int(bbox["y0"])
        x1 = int(bbox["x1"])
        y1 = int(bbox["y1"])

        # Ensure coordinates are within image bounds
        height, width = img.shape[:2]
        x0 = max(0, min(x0, width))
        y0 = max(0, min(y0, height))
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))

        if x1 <= x0 or y1 <= y0:
            return None

        cropped = img[y0:y1, x0:x1]
        return cropped
    except Exception as e:
        logger.error(f"Error cropping table region: {e}")
        return None


# V8: Track PaddleOCR failures to skip after repeated failures
_paddleocr_failure_count = 0
_paddleocr_max_failures = 3  # Skip after 3 consecutive failures


def extract_table_with_paddleocr(table_image: np.ndarray, table_id: str) -> Table | None:
    """Extract table structure using PaddleOCR PP-StructureV3."""
    global _paddleocr_failure_count
    
    # V8: Skip if PaddleOCR has failed too many times
    if _paddleocr_failure_count >= _paddleocr_max_failures:
        logger.debug(f"Skipping PaddleOCR for {table_id} (too many previous failures)")
        return None
    
    try:
        from paddleocr import PaddleOCR, PPStructure

        # Check CUDA availability
        try:
            import torch
            use_gpu = torch.cuda.is_available()
            if use_gpu:
                logger.debug(f"Using CUDA for PP-StructureV3: {torch.cuda.get_device_name(0)}")
            else:
                logger.warning("CUDA not available, using CPU for PP-StructureV3 (slower)")
        except ImportError:
            use_gpu = False
            logger.warning("PyTorch not available, using CPU for PP-StructureV3")

        # Initialize PP-Structure with GPU if available
        structure_engine = PPStructure(show_log=False, use_gpu=use_gpu)
        
        if use_gpu:
            logger.info(f"PP-StructureV3 initialized with GPU for table {table_id}")

        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(cv2.cvtColor(table_image, cv2.COLOR_BGR2RGB))

        # Run structure analysis
        result = structure_engine(pil_image)

        # Parse PP-Structure result
        cells: list[Cell] = []
        grid: dict[str, list[str]] = {}

        if result and len(result) > 0:
            # PP-Structure returns list of dicts with 'type' and 'bbox' and 'res'
            for item in result:
                if item.get("type") == "table":
                    table_data = item.get("res", {})
                    html = table_data.get("html", "")

                    # Try to parse HTML table structure
                    # This is a simplified parser - PP-StructureV3 provides HTML
                    # For full implementation, use html.parser or BeautifulSoup
                    if html:
                        # Simple extraction: look for <td> tags
                        import re

                        td_pattern = r"<td[^>]*>(.*?)</td>"
                        matches = re.findall(td_pattern, html, re.DOTALL)

                        row = 0
                        col = 0
                        max_cols = 0

                        for match in matches:
                            text = re.sub(r"<[^>]+>", "", match).strip()
                            cell = Cell(
                                row=row,
                                col=col,
                                text_raw=text,
                                value_num=None,
                                unit=None,
                                bbox=None,
                                confidence=0.8,
                            )
                            cells.append(cell)

                            # Update grid
                            if str(col) not in grid:
                                grid[str(col)] = []
                            while len(grid[str(col)]) <= row:
                                grid[str(col)].append("")
                            grid[str(col)][row] = text

                            col += 1
                            max_cols = max(max_cols, col)

                            # Simple row detection (newline or </tr>)
                            if "</tr>" in match or "\n" in match:
                                row += 1
                                col = 0

        # Get bbox from image
        height, width = table_image.shape[:2]
        bbox = BBox(x0=0.0, y0=0.0, x1=float(width), y1=float(height))

        if cells:
            table = Table(
                table_id=table_id,
                bbox=bbox,
                source=SourceType.OCR,
                confidence=0.8,
                cells=cells,
                grid=grid,
            )
            return table

        return None

    except ImportError:
        logger.warning("PaddleOCR not available, skipping PP-StructureV3")
        _paddleocr_failure_count = _paddleocr_max_failures  # Disable permanently
        return None
    except Exception as e:
        _paddleocr_failure_count += 1
        if _paddleocr_failure_count >= _paddleocr_max_failures:
            logger.warning(f"PaddleOCR failed {_paddleocr_failure_count} times, disabling: {e}")
        else:
            logger.error(f"Error extracting table with PaddleOCR: {e}")
        return None


def extract_table_with_fallback(table_image: np.ndarray, table_id: str) -> Table | None:
    """Fallback: use OpenCV grid detection + OCR."""
    try:
        gray = cv2.cvtColor(table_image, cv2.COLOR_BGR2GRAY)

        # Detect grid lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)

        # Find intersections to create grid
        # This is simplified - full implementation would detect all intersections
        cells: list[Cell] = []
        grid: dict[str, list[str]] = {}

        # Simple OCR on whole image as fallback
        try:
            import pytesseract

            text = pytesseract.image_to_string(table_image)
            # Split into rough cells (very basic)
            lines = text.split("\n")
            for row, line in enumerate(lines):
                if line.strip():
                    parts = line.split()  # Simple word splitting
                    for col, part in enumerate(parts):
                        cell = Cell(
                            row=row,
                            col=col,
                            text_raw=part,
                            value_num=None,
                            unit=None,
                            bbox=None,
                            confidence=0.5,
                        )
                        cells.append(cell)

                        if str(col) not in grid:
                            grid[str(col)] = []
                        while len(grid[str(col)]) <= row:
                            grid[str(col)].append("")
                        grid[str(col)][row] = part

        except ImportError:
            logger.warning("pytesseract not available for fallback OCR")

        if cells:
            height, width = table_image.shape[:2]
            bbox = BBox(x0=0.0, y0=0.0, x1=float(width), y1=float(height))

            table = Table(
                table_id=table_id,
                bbox=bbox,
                source=SourceType.OCR,
                confidence=0.5,
                cells=cells,
                grid=grid,
            )
            return table

        return None

    except Exception as e:
        logger.error(f"Error in fallback table extraction: {e}")
        return None


def extract_ocr_text_blocks(
    image_path: Path, text_regions: list[dict[str, Any]], page_index: int
) -> list[Block]:
    """Extract text blocks from text regions using OCR (V5: Tesseract primary)."""
    from src.schemas.models import Block, BlockType, BBox, SourceType

    blocks: list[Block] = []
    ocr_source_used: str | None = None
    paddle_blocks = 0
    tesseract_blocks = 0

    # V5: Use OCR_PRIMARY setting to determine which OCR to use first
    ocr_primary = settings.ocr_primary
    ocr_fallback = settings.ocr_fallback

    # V5: Try primary OCR first
    if ocr_primary == "tesseract":
        # Use Tesseract as primary
        tesseract_blocks = _extract_with_tesseract(image_path, text_regions, page_index, blocks)
        if tesseract_blocks > 0:
            ocr_source_used = "tesseract"
            logger.info(f"Page {page_index}: Tesseract extracted {tesseract_blocks} blocks")
        elif ocr_fallback == "paddle":
            # Fallback to PaddleOCR if Tesseract failed
            logger.warning(f"Page {page_index}: Tesseract returned 0 blocks, trying PaddleOCR fallback")
            paddle_blocks = _extract_with_paddleocr(image_path, text_regions, page_index, blocks)
            if paddle_blocks > 0:
                ocr_source_used = "paddle"
                logger.info(f"Page {page_index}: PaddleOCR fallback extracted {paddle_blocks} blocks")
    elif ocr_primary == "paddle":
        # Use PaddleOCR as primary
        paddle_blocks = _extract_with_paddleocr(image_path, text_regions, page_index, blocks)
        if paddle_blocks > 0:
            ocr_source_used = "paddle"
            logger.info(f"Page {page_index}: PaddleOCR extracted {paddle_blocks} blocks")
        elif ocr_fallback == "tesseract":
            # Fallback to Tesseract if PaddleOCR failed
            logger.warning(f"Page {page_index}: PaddleOCR returned 0 blocks, trying Tesseract fallback")
            tesseract_blocks = _extract_with_tesseract(image_path, text_regions, page_index, blocks)
            if tesseract_blocks > 0:
                ocr_source_used = "tesseract"
                logger.info(f"Page {page_index}: Tesseract fallback extracted {tesseract_blocks} blocks")

    # V5: Log OCR results per page
    logger.info(f"Page {page_index} OCR summary: paddle={paddle_blocks}, tesseract={tesseract_blocks}, source={ocr_source_used}, total={len(blocks)}")

    # V5: If no blocks extracted, log warning
    if len(blocks) == 0:
        logger.error(f"Page {page_index}: No OCR blocks extracted! Primary={ocr_primary}, Fallback={ocr_fallback}")

    return blocks


def _run_tesseract_with_psm(
    pil_image: Any, psm: int, lang: str, oem: int
) -> tuple[str, dict[str, Any]]:
    """
    Run Tesseract OCR with specific PSM and return text + quality metrics.
    
    Returns:
        Tuple of (text, quality_metrics)
    """
    import pytesseract
    from src.pipeline.step_42_ocr_quality import calculate_ocr_quality_metrics
    
    tess_config = f"--psm {psm} --oem {oem}"
    
    try:
        text = pytesseract.image_to_string(pil_image, lang=lang, config=tess_config)
    except Exception as e:
        logger.warning(f"Tesseract PSM={psm} failed: {e}")
        return "", {"status": "error", "score": 0.0, "repeat_run_max": 999}
    
    quality_metrics = calculate_ocr_quality_metrics(text)
    quality_metrics["psm"] = psm
    
    return text, quality_metrics


def _preprocess_with_mode(
    crop: np.ndarray, mode: str
) -> Any:
    """
    Preprocess image crop with specified mode and return PIL image.
    
    Args:
        crop: Image crop as numpy array
        mode: Preprocessing mode ("standard", "aggressive", "minimal")
    
    Returns:
        PIL Image
    """
    from PIL import Image
    from src.ocr.preprocess import preprocess_for_ocr
    import tempfile
    
    # Save crop temporarily for preprocessing
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        cv2.imwrite(str(tmp_path), crop)
    
    try:
        preprocessed = preprocess_for_ocr(tmp_path, mode=mode)
        pil_image = Image.fromarray(preprocessed)
    finally:
        tmp_path.unlink(missing_ok=True)
    
    return pil_image


def _select_best_ocr_pass(
    results: list[tuple[str, dict[str, Any], int]]
) -> tuple[str, int, dict[str, Any]]:
    """
    Select best OCR pass based on quality metrics (V8).
    
    Selection criteria (in order of importance):
    1. Lowest repeat_run_max (penalize noise heavily)
    2. Highest alpha_ratio
    3. Lowest junk_token_ratio
    4. Tie-breaker: higher score
    
    Returns:
        Tuple of (best_text, pass_used, quality_metrics)
    """
    if not results:
        return "", 1, {"status": "empty", "score": 0.0}
    
    def score_result(result: tuple[str, dict[str, Any], int]) -> tuple[float, float]:
        """
        Calculate composite score for selection.
        
        Returns:
            Tuple of (primary_score, secondary_score)
            - primary_score: penalizes high repeat_run_max heavily
            - secondary_score: general quality score
        """
        text, metrics, _ = result
        alpha_ratio = metrics.get("alpha_ratio", 0.0)
        repeat_run = metrics.get("repeat_run_max", 20)
        junk_ratio = metrics.get("junk_token_ratio", 1.0)
        avg_word_len = metrics.get("avg_word_len", 0.0)
        
        # Primary score: heavily penalize repeat_run_max >= 8
        # If repeat_run >= 10, this is "bad" OCR
        if repeat_run >= 10:
            primary = -repeat_run  # Very negative for bad noise
        elif repeat_run >= 8:
            primary = 10 - repeat_run  # Slightly negative
        else:
            primary = 20 - repeat_run  # Positive for good results
        
        # Secondary score: general quality
        secondary = (
            alpha_ratio * 0.4
            + (1.0 - junk_ratio) * 0.3
            + min(avg_word_len / 8.0, 1.0) * 0.2
            + metrics.get("score", 0.0) * 0.1
        )
        
        return (primary, secondary)
    
    # Sort by (primary, secondary) descending
    scored = [(r, score_result(r)) for r in results]
    scored.sort(key=lambda x: (x[1][0], x[1][1]), reverse=True)
    
    best = scored[0][0]
    best_scores = scored[0][1]
    
    # Log selection details if multiple passes
    if len(results) > 1:
        logger.debug(
            f"Pass selection: chose pass {best[2]} with primary={best_scores[0]:.1f}, "
            f"secondary={best_scores[1]:.2f}, repeat_run={best[1].get('repeat_run_max', 0)}"
        )
    
    return best[0], best[2], best[1]


def _extract_with_tesseract(
    image_path: Path, text_regions: list[dict[str, Any]], page_index: int, blocks: list[Block]
) -> int:
    """Extract text blocks using Tesseract OCR with adaptive PSM (V8)."""
    from src.schemas.models import Block, BlockType, BBox, SourceType
    from src.pipeline.step_42_ocr_quality import calculate_ocr_quality_metrics

    blocks_count = 0

    try:
        import pytesseract
        from PIL import Image

        # V5: Configure pytesseract path if set in config
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = str(settings.tesseract_cmd)

        for region_idx, region in enumerate(text_regions):
            bbox_dict = region["bbox"]
            x0, y0, x1, y1 = bbox_dict["x0"], bbox_dict["y0"], bbox_dict["x1"], bbox_dict["y1"]

            img = cv2.imread(str(image_path))
            if img is None:
                continue

            height, width = img.shape[:2]
            x0_int = max(0, int(x0))
            y0_int = max(0, int(y0))
            x1_int = min(width, int(x1))
            y1_int = min(height, int(y1))

            if x1_int <= x0_int or y1_int <= y0_int:
                continue

            crop = img[y0_int:y1_int, x0_int:x1_int]
            
            # Skip if crop is too small
            if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
                continue

            # V8: Preprocess with standard mode first
            pil_image = _preprocess_with_mode(crop, "standard")
            
            # V8: Adaptive PSM - run pass 1 with default PSM
            pass1_text, pass1_metrics = _run_tesseract_with_psm(
                pil_image, settings.tess_psm, settings.tess_lang, settings.tess_oem
            )
            
            # Check if pass 1 quality is bad
            is_bad_quality = (
                pass1_metrics.get("status") == "bad"
                or pass1_metrics.get("repeat_run_max", 0) >= 10
                or (pass1_metrics.get("alpha_ratio", 1.0) < 0.3 
                    and pass1_metrics.get("digit_ratio", 1.0) < 0.05)
            )
            
            # Store all pass results: (text, metrics, pass_num)
            all_passes: list[tuple[str, dict[str, Any], int]] = [(pass1_text, pass1_metrics, 1)]
            
            # V8: If bad quality, try additional PSMs with different preprocessing
            if is_bad_quality and pass1_text:
                logger.debug(f"Page {page_index} region {region_idx}: Bad quality (repeat_run={pass1_metrics.get('repeat_run_max')}), trying adaptive PSM")
                
                # Pass 2: PSM=11 (sparse text) with standard preprocessing
                pass2_text, pass2_metrics = _run_tesseract_with_psm(
                    pil_image, 11, settings.tess_lang, settings.tess_oem
                )
                if pass2_text:
                    all_passes.append((pass2_text, pass2_metrics, 2))
                
                # Pass 3: Use AGGRESSIVE preprocessing + PSM=3 (auto)
                # This helps with noisy scanned documents
                if pass2_metrics.get("repeat_run_max", 0) >= 8:
                    logger.debug(f"Page {page_index} region {region_idx}: Still noisy, trying aggressive preprocessing")
                    pil_image_aggressive = _preprocess_with_mode(crop, "aggressive")
                    
                    pass3_text, pass3_metrics = _run_tesseract_with_psm(
                        pil_image_aggressive, 3, settings.tess_lang, settings.tess_oem
                    )
                    if pass3_text:
                        pass3_metrics["preprocess"] = "aggressive"
                        all_passes.append((pass3_text, pass3_metrics, 3))
                    
                    # Pass 4: Aggressive + PSM=4 (single column) - last resort
                    if pass3_metrics.get("repeat_run_max", 0) >= 8:
                        pass4_text, pass4_metrics = _run_tesseract_with_psm(
                            pil_image_aggressive, 4, settings.tess_lang, settings.tess_oem
                        )
                        if pass4_text:
                            pass4_metrics["preprocess"] = "aggressive"
                            all_passes.append((pass4_text, pass4_metrics, 4))
            
            # V8: Select best pass
            best_text, pass_used, best_metrics = _select_best_ocr_pass(all_passes)
            
            if len(all_passes) > 1:
                logger.info(
                    f"Page {page_index} region {region_idx}: Adaptive PSM selected pass {pass_used} "
                    f"(score={best_metrics.get('score', 0):.2f}, repeat_run={best_metrics.get('repeat_run_max', 0)})"
                )

            if best_text.strip():
                block_id = f"p{page_index}_b_ocr_{region_idx}"
                block = Block(
                    block_id=block_id,
                    type=BlockType.TEXT,
                    text=best_text.strip(),
                    bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
                    source=SourceType.OCR,
                    confidence=0.6,
                    ocr_pass_used=pass_used,  # V8: Track which pass was used
                )
                blocks.append(block)
                blocks_count += 1
                logger.debug(f"Extracted Tesseract block {block_id}: {len(best_text.strip())} chars (pass {pass_used})")

    except ImportError:
        logger.error("pytesseract not available - install pytesseract!")
    except Exception as tesseract_err:
        logger.error(f"Tesseract OCR failed: {tesseract_err}")

    return blocks_count


def _extract_with_paddleocr(
    image_path: Path, text_regions: list[dict[str, Any]], page_index: int, blocks: list[Block]
) -> int:
    """Extract text blocks using PaddleOCR (V5: isolated, optional)."""
    from src.schemas.models import Block, BlockType, BBox, SourceType

    blocks_count = 0

    try:
        from paddleocr import PaddleOCR
        import torch

        # V4: Use OCR device from config (default: CPU for stability)
        ocr_device = settings.ocr_device
        if ocr_device == "auto":
            use_gpu = torch.cuda.is_available() if torch.cuda.is_available() else False
        elif ocr_device == "cuda":
            use_gpu = torch.cuda.is_available()
            if not use_gpu:
                logger.warning("CUDA requested but not available, falling back to CPU")
                use_gpu = False
        else:
            use_gpu = False
        
        # V4: Disable MKLDNN to avoid OneDnnContext errors
        use_mkldnn = settings.ocr_use_mkldnn
        
        # Use "en" for Latin-based languages (Finnish uses Latin script)
        # PaddleOCR doesn't support "fin" directly
        logger.debug(f"Initializing PaddleOCR (device: {'GPU' if use_gpu else 'CPU'}, MKLDNN: {use_mkldnn}) for {len(text_regions)} regions on page {page_index}")
        try:
            # V4: Set environment variable to disable MKLDNN if needed
            if not use_mkldnn:
                os.environ["FLAGS_use_mkldnn"] = "0"
            
            ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
                use_gpu=use_gpu,
                use_mkldnn=use_mkldnn,
            )
            logger.debug(f"PaddleOCR initialized successfully with device={'GPU' if use_gpu else 'CPU'}")
        except Exception as paddle_init_err:
            logger.warning(f"PaddleOCR init failed ({paddle_init_err}), falling back to CPU without MKLDNN")
            use_gpu = False
            os.environ["FLAGS_use_mkldnn"] = "0"
            ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False, use_gpu=False, use_mkldnn=False)
            logger.debug(f"PaddleOCR initialized with CPU fallback (MKLDNN disabled)")

        for region_idx, region in enumerate(text_regions):
            logger.debug(f"Processing region {region_idx}/{len(text_regions)} on page {page_index}")
            bbox_dict = region["bbox"]
            x0, y0, x1, y1 = bbox_dict["x0"], bbox_dict["y0"], bbox_dict["x1"], bbox_dict["y1"]

            # Crop region
            img = cv2.imread(str(image_path))
            if img is None:
                continue

            height, width = img.shape[:2]
            x0_int = max(0, int(x0))
            y0_int = max(0, int(y0))
            x1_int = min(width, int(x1))
            y1_int = min(height, int(y1))

            if x1_int <= x0_int or y1_int <= y0_int:
                continue

            crop = img[y0_int:y1_int, x0_int:x1_int]
            
            # V2: Skip if crop is too small
            if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
                logger.debug(f"Skipping region {region_idx} on page {page_index}: crop too small")
                continue

            # Run OCR
            try:
                result = ocr.ocr(crop, cls=True)
                if result and result[0] and len(result[0]) > 0:
                    # Combine all text from OCR results
                    text_parts: list[str] = []
                    for line in result[0]:
                        if line and len(line) >= 2:
                            text_parts.append(line[1][0])  # text content

                    if text_parts:
                        combined_text = " ".join(text_parts)
                        block_id = f"p{page_index}_b_ocr_{region_idx}"

                        block = Block(
                            block_id=block_id,
                            type=BlockType.TEXT,
                            text=combined_text,
                            bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
                            source=SourceType.OCR,
                            confidence=0.8,  # OCR confidence
                        )
                        blocks.append(block)
                        blocks_count += 1
                        logger.debug(f"Extracted PaddleOCR block {block_id}: {len(combined_text)} chars")
                    else:
                        logger.debug(f"OCR returned no text for region {region_idx} on page {page_index}")
                else:
                    logger.debug(f"OCR returned empty result for region {region_idx} on page {page_index}")
            except Exception as ocr_err:
                logger.warning(f"PaddleOCR error for region {region_idx} on page {page_index}: {ocr_err}")

    except (ImportError, Exception) as paddle_err:
        logger.warning(f"PaddleOCR failed ({paddle_err})")

    return blocks_count


def process_ocr_tables(
    rendered_pages: dict[int, Path],
    regions: dict[int, list[dict[str, Any]]],
    output_dir: Path,
    debug_dir: Path,
) -> tuple[dict[int, list[Table]], dict[int, list[Block]]]:
    """Process OCR table and text extraction for scan/mixed pages."""
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Log GPU status
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"Processing OCR with CUDA: {torch.cuda.get_device_name(0)}")
        else:
            logger.warning("CUDA not available - OCR will use CPU (much slower)")
    except ImportError:
        logger.warning("PyTorch not available - OCR will use CPU")

    all_tables: dict[int, list[Table]] = {}
    all_ocr_blocks: dict[int, list[Block]] = {}

    for page_index, image_path in rendered_pages.items():
        page_regions = regions.get(page_index, [])
        page_tables: list[Table] = []

        # 41A) Extract tables
        table_regions = [r for r in page_regions if r.get("type") == "table"]

        for table_idx, region in enumerate(table_regions):
            table_id = f"p{page_index}_t{table_idx}"

            # Crop table region
            table_image = crop_table_region(image_path, region["bbox"])
            if table_image is None:
                continue

            # Save debug crop
            crop_path = debug_dir / f"table_crop_p{page_index}_t{table_idx}.png"
            cv2.imwrite(str(crop_path), table_image)

            # Try PaddleOCR PP-StructureV3 first
            table = extract_table_with_paddleocr(table_image, table_id)

            # Fallback to OpenCV + OCR
            if table is None:
                table = extract_table_with_fallback(table_image, table_id)

            if table:
                page_tables.append(table)
                logger.info(f"Extracted OCR table {table_id} with {len(table.cells)} cells")

        all_tables[page_index] = page_tables

        # 41B) Extract text regions (V2: ALWAYS run for scan/mixed pages)
        text_regions = [r for r in page_regions if r.get("type") == "text"]
        
        # V2: If no text regions detected, create a full-page region as fallback
        # This ensures we ALWAYS get some data from scan pages
        if not text_regions:
            logger.warning(f"V2: No text regions detected for page {page_index}, using full-page OCR as fallback")
            img = cv2.imread(str(image_path))
            if img is not None:
                height, width = img.shape[:2]
                text_regions = [{
                    "type": "text",
                    "bbox": {"x0": 0.0, "y0": 0.0, "x1": float(width), "y1": float(height)},
                    "confidence": 0.5,
                }]
        
        # V2: ALWAYS extract OCR text (even if regions are empty, fallback was created above)
        if text_regions:
            ocr_blocks = extract_ocr_text_blocks(image_path, text_regions, page_index)
            all_ocr_blocks[page_index] = ocr_blocks
            if len(ocr_blocks) > 0:
                logger.info(f"Extracted {len(ocr_blocks)} OCR text blocks from page {page_index}")
            else:
                logger.warning(f"V2: OCR text extraction returned 0 blocks for page {page_index}")
        else:
            logger.error(f"V2 CRITICAL: No text regions and fallback failed for page {page_index}")
            all_ocr_blocks[page_index] = []

        # Save tables to JSONL
        output_file = output_dir / "ocr_tables.jsonl"
        with open(output_file, "a", encoding="utf-8") as f:
            for table in page_tables:
                f.write(table.model_dump_json() + "\n")

    return all_tables, all_ocr_blocks


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 4:
        print("Usage: python step_41_ocr_tables.py <rendered_pages_json> <regions_json> <output_dir>")
        sys.exit(1)

    # This would be called from run_all.py with proper data structures
    print("This step is typically called from run_all.py")
