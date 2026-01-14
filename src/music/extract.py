"""Music sheet metadata extraction using OCR."""

import logging
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from src.schemas.models import MusicMetadata, Block, BlockType, BBox, SourceType

logger = logging.getLogger(__name__)

# Dynamic markings patterns (case-insensitive matching)
DYNAMICS = [
    "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff",
    "sfz", "sfp", "fp", "rf", "rfz", "fz",
]

# Expression markings patterns
EXPRESSIONS = [
    "cresc", "decresc", "dim", "crescendo", "diminuendo",
    "rit", "ritard", "ritardando", "rall", "rallentando",
    "accel", "accelerando", "a tempo", "tempo primo",
    "poco a poco", "subito", "molto", "sempre",
    "dolce", "espressivo", "cantabile", "legato", "staccato",
    "marcato", "tenuto", "pizz", "arco",
    "tasto", "ponticello", "normale", "metallico",
    "tambora", "rasgueado", "rasg", "golpe",
    "lontano", "misterioso", "con fuoco", "con brio",
    "l.v.", "let vibrate", "in tempo",
]

# Minimum confidence threshold for OCR blocks
MIN_OCR_CONFIDENCE = 0.55

# Known noise patterns from musical notation OCR
NOISE_PATTERNS = {
    "fer", "ep", "ef", "eff", "wth", "leap", "ty", "ocr", "or", "op", 
    "of", "oe", "oer", "rer", "ee", "ff", "rr", "tt", "hh",
}

# Valid music text whitelist (lowercase)
MUSIC_TEXT_WHITELIST = set(DYNAMICS) | set(EXPRESSIONS) | {
    # Common tempo markings
    "andante", "allegro", "adagio", "presto", "moderato", "largo",
    "lento", "vivace", "grave", "maestoso",
    # Guitar specific
    "cvii", "cvi", "cv", "civ", "ciii", "cii", "ci",  # Capo positions
    "harm", "harmonics", "nat", "natural",
    # Dynamics extensions  
    "cresc", "dim", "decresc",
}


def is_valid_music_text(text: str, confidence: float, region: str) -> bool:
    """
    Filter out OCR noise - only keep valid music-related text.
    
    Args:
        text: OCR text
        confidence: OCR confidence (0-1)
        region: Region name (header, footer, between_staff, etc.)
    
    Returns:
        True if text should be kept
    """
    text_lower = text.lower().strip()
    
    # Always reject low confidence
    if confidence < MIN_OCR_CONFIDENCE:
        return False
    
    # Reject known noise patterns
    if text_lower in NOISE_PATTERNS:
        return False
    
    # Reject very short tokens that aren't dynamics
    if len(text_lower) <= 2 and text_lower not in DYNAMICS:
        # Allow measure numbers (digits)
        if not text.isdigit():
            return False
    
    # Header region: be more permissive (title, composer, dedication)
    if region == "header":
        # Accept longer text with high confidence
        if len(text) >= 3 and confidence >= 0.7:
            return True
        # Accept if it looks like a name (capitalized)
        if text[0].isupper() and len(text) >= 4:
            return True
    
    # Between-staff regions: only accept whitelisted music terms
    if region.startswith("between_staff"):
        if text_lower in MUSIC_TEXT_WHITELIST:
            return True
        # Accept measure numbers
        if text.isdigit() and int(text) < 500:
            return True
        # Reject everything else from between-staff
        return confidence >= 0.8 and len(text) >= 4
    
    # Footer: accept copyright, page numbers
    if region == "footer":
        if "©" in text or text.isdigit():
            return True
        return confidence >= 0.7
    
    return True


def _is_in_staff_area(y: int, staves: list[dict[str, Any]], margin: int = 30) -> bool:
    """Check if y-coordinate falls within any staff area (with margin)."""
    for staff in staves:
        staff_top = staff["top_y"] - margin
        staff_bottom = staff["bottom_y"] + margin
        if staff_top <= y <= staff_bottom:
            return True
    return False


def extract_text_regions_ocr(
    image: np.ndarray, staves: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Extract text regions from music sheet, AVOIDING staff lines.
    
    Staff areas are MASKED to prevent OCR noise from musical notation.
    Text typically appears:
    - Above the first staff (title, composer)
    - Between staves (dynamics, expressions) - but NOT on staff lines
    - At bottom (copyright)
    - Left margin (measure numbers)
    
    Args:
        image: Input image
        staves: Detected staff positions
    
    Returns:
        List of text region dicts with bbox and OCR text
    """
    try:
        import pytesseract
        from PIL import Image
        from src.pipeline.config import get_settings
        
        settings = get_settings()
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = str(settings.tesseract_cmd)
    except ImportError:
        logger.error("pytesseract not available")
        return []
    
    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    height, width = gray.shape
    
    # Define regions of interest - ONLY areas OUTSIDE staff lines
    regions: list[dict[str, Any]] = []
    
    # Region 1: Header (top of page, above first staff)
    if staves:
        header_bottom = staves[0]["top_y"] - 20
    else:
        header_bottom = int(height * 0.15)
    
    header_region = gray[0:max(10, header_bottom), :]
    if header_region.size > 0:
        regions.append({
            "name": "header",
            "image": header_region,
            "y_offset": 0,
            "x_offset": 0,
        })
    
    # Region 2: Footer (below last staff)
    if staves:
        footer_top = staves[-1]["bottom_y"] + 40
    else:
        footer_top = int(height * 0.92)
    
    if footer_top < height - 10:
        footer_region = gray[footer_top:height, :]
        if footer_region.size > 0:
            regions.append({
                "name": "footer",
                "image": footer_region,
                "y_offset": footer_top,
                "x_offset": 0,
            })
    
    # Region 3: Left margin (measure numbers) - but mask staff y-ranges
    # Only get narrow left strip, avoiding staff lines
    left_margin_width = int(width * 0.06)
    
    # Region 4: Between staves (dynamics, expressions)
    # These are the gaps BETWEEN staff systems, not ON the staves
    for i in range(len(staves) - 1):
        current_staff_bottom = staves[i]["bottom_y"] + 15  # Small margin below
        next_staff_top = staves[i + 1]["top_y"] - 15  # Small margin above
        
        if next_staff_top > current_staff_bottom + 10:  # At least 10px gap
            between_region = gray[current_staff_bottom:next_staff_top, 
                                  int(width * 0.05):int(width * 0.95)]
            if between_region.size > 0:
                regions.append({
                    "name": f"between_staff_{i}_{i+1}",
                    "image": between_region,
                    "y_offset": current_staff_bottom,
                    "x_offset": int(width * 0.05),
                })
    
    # NOTE: We deliberately DO NOT OCR the staff areas themselves
    # This prevents noise like "FER/EP/EF/EFF" from musical notation
    
    # OCR each region
    text_blocks: list[dict[str, Any]] = []
    
    for region in regions:
        try:
            pil_image = Image.fromarray(region["image"])
            
            # Use Tesseract with layout analysis
            data = pytesseract.image_to_data(
                pil_image,
                lang="eng+ita",  # Italian for music terms
                output_type=pytesseract.Output.DICT,
            )
            
            for i, text in enumerate(data["text"]):
                if text.strip():
                    x = data["left"][i] + region["x_offset"]
                    y = data["top"][i] + region["y_offset"]
                    w = data["width"][i]
                    h = data["height"][i]
                    conf = data["conf"][i] / 100.0  # Normalize to 0-1
                    text_clean = text.strip()

                    # Apply noise filtering
                    if is_valid_music_text(text_clean, conf, region["name"]):
                        text_blocks.append({
                            "text": text_clean,
                            "bbox": {"x0": x, "y0": y, "x1": x + w, "y1": y + h},
                            "confidence": conf,
                            "region": region["name"],
                        })
                    else:
                        logger.debug(f"Filtered noise: '{text_clean}' (conf={conf:.2f}, region={region['name']})")
        except Exception as e:
            logger.warning(f"OCR failed for region {region['name']}: {e}")
    
    return text_blocks


def classify_music_text(text: str) -> tuple[BlockType, str | None]:
    """
    Classify a text string as music-specific type.
    
    Dynamics are normalized to lowercase (p, mf, f, etc.)
    
    Returns:
        Tuple of (BlockType, normalized_text)
    """
    text_lower = text.lower().strip()
    
    # Check dynamics (case-insensitive, normalize to lowercase)
    for dyn in DYNAMICS:
        if text_lower == dyn:
            return BlockType.MUSIC_DYNAMIC, dyn  # Always lowercase
    
    # Check expressions
    for expr in EXPRESSIONS:
        if expr in text_lower:
            return BlockType.MUSIC_EXPRESSION, text.strip()
    
    # Check tempo (contains "=" and number, or metronome mark)
    if "=" in text and any(c.isdigit() for c in text):
        return BlockType.MUSIC_TEMPO, text.strip()
    
    # Check measure numbers (standalone numbers at left margin)
    if text.isdigit() and int(text) < 500:
        return BlockType.MUSIC_MEASURE_NUM, text
    
    # Default to regular text
    return BlockType.TEXT, text.strip()


def extract_music_metadata(
    image: np.ndarray,
    staves: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
) -> MusicMetadata:
    """
    Extract structured music metadata from detected elements.
    
    Args:
        image: Input image
        staves: Detected staff systems
        text_blocks: OCR text blocks
    
    Returns:
        MusicMetadata object
    """
    metadata = MusicMetadata()
    
    # Find title (usually largest text in header, centered)
    header_texts = [t for t in text_blocks if t.get("region") == "header"]
    
    # Sort by y-position (top first)
    header_texts.sort(key=lambda t: t["bbox"]["y0"])
    
    if header_texts:
        # Combine nearby text blocks on same line for better parsing
        combined_lines: list[str] = []
        current_line: list[str] = []
        last_y = -100
        
        for block in header_texts:
            y = block["bbox"]["y0"]
            if abs(y - last_y) < 15:  # Same line
                current_line.append(block["text"])
            else:
                if current_line:
                    combined_lines.append(" ".join(current_line))
                current_line = [block["text"]]
                last_y = y
        if current_line:
            combined_lines.append(" ".join(current_line))
        
        # Analyze combined lines
        # Finnish music sheets often have: dedication (small), title (large), composer (medium)
        for i, line in enumerate(combined_lines):
            line_lower = line.lower()
            line_clean = re.sub(r'[^a-zA-ZäöåÄÖÅ\s\-]', '', line).strip()
            
            # Check for dedication patterns
            is_dedication = (
                "omistettu" in line_lower or 
                "dedicated" in line_lower or
                "für" in line_lower or
                "for" in line_lower or
                # First line with name pattern (e.g., "Kai Niemiselle")
                (i == 0 and re.search(r"[A-ZÄÖÅ][a-zäöå]+\s+[A-ZÄÖÅ][a-zäöå]+", line_clean))
            )
            
            if is_dedication and not metadata.dedication:
                metadata.dedication = line
            # Composer: contains years (1997-2001)
            elif re.search(r"\d{4}", line):
                # Clean up OCR artifacts
                composer_text = re.sub(r'^[a-z]\s+', '', line)  # Remove single char prefix
                composer_text = re.sub(r'\s+\d$', '', composer_text)  # Remove trailing single digit
                metadata.composer = composer_text.strip()
            # Title: usually short, no years, not a name pattern
            elif not metadata.title:
                if len(line) < 30 and not re.search(r"\d{4}", line):
                    # Skip if it's already identified as dedication
                    if line != metadata.dedication:
                        metadata.title = line
        
        # If title still not found, look for short alphanumeric strings (like "7x7")
        if not metadata.title:
            for block in header_texts:
                text = block["text"].strip()
                # Title is often short and may contain x or numbers
                if len(text) < 15 and text not in (metadata.dedication or ""):
                    if text != metadata.composer:
                        metadata.title = text
                        break
    
    # Find copyright (usually in footer)
    footer_texts = [t for t in text_blocks if t.get("region") == "footer"]
    for block in footer_texts:
        if "©" in block["text"] or "copyright" in block["text"].lower():
            metadata.copyright = block["text"]
    
    # Collect dynamics
    dynamics_found: set[str] = set()
    for block in text_blocks:
        block_type, normalized = classify_music_text(block["text"])
        if block_type == BlockType.MUSIC_DYNAMIC and normalized:
            dynamics_found.add(normalized)
    metadata.dynamics = sorted(list(dynamics_found))
    
    # Collect expressions
    expressions_found: set[str] = set()
    for block in text_blocks:
        block_type, normalized = classify_music_text(block["text"])
        if block_type == BlockType.MUSIC_EXPRESSION and normalized:
            expressions_found.add(normalized)
    metadata.expressions = sorted(list(expressions_found))
    
    # Find tempo marking
    for block in text_blocks:
        block_type, normalized = classify_music_text(block["text"])
        if block_type == BlockType.MUSIC_TEMPO and normalized:
            metadata.tempo = normalized
            break
    
    # Count measures from measure numbers
    measure_nums: list[int] = []
    for block in text_blocks:
        block_type, normalized = classify_music_text(block["text"])
        if block_type == BlockType.MUSIC_MEASURE_NUM and normalized:
            try:
                measure_nums.append(int(normalized))
            except ValueError:
                pass
    
    if measure_nums:
        metadata.measure_count = max(measure_nums)
    
    # Staff count
    if staves:
        # Estimate based on number of staves
        logger.debug(f"Detected {len(staves)} staff systems")
    
    return metadata


def process_music_sheet(image_path: Path | str, run_omr: bool = True) -> dict[str, Any]:
    """
    Process a music sheet image and extract all structured data.
    
    Args:
        image_path: Path to music sheet image
        run_omr: Whether to attempt OMR (Audiveris) for note extraction
    
    Returns:
        Dictionary with all extracted data
    """
    from src.music.detect import is_music_sheet
    from src.music.omr import run_audiveris, omr_result_to_dict, find_audiveris
    
    image_path = Path(image_path)
    image = cv2.imread(str(image_path))
    if image is None:
        return {"error": f"Could not read image: {image_path}"}
    
    # Detect if it's a music sheet
    is_music, confidence, detection_info = is_music_sheet(image)
    
    if not is_music:
        return {
            "is_music_sheet": False,
            "confidence": confidence,
            "detection_info": detection_info,
        }
    
    staves = detection_info.get("staves", [])
    
    # Extract text via OCR
    text_blocks = extract_text_regions_ocr(image, staves)
    
    # Extract metadata
    metadata = extract_music_metadata(image, staves, text_blocks)
    
    # Build blocks for items
    blocks: list[Block] = []
    
    for i, block_data in enumerate(text_blocks):
        block_type, _ = classify_music_text(block_data["text"])
        bbox = block_data["bbox"]
        
        block = Block(
            block_id=f"music_b_{i}",
            type=block_type,
            text=block_data["text"],
            bbox=BBox(
                x0=float(bbox["x0"]),
                y0=float(bbox["y0"]),
                x1=float(bbox["x1"]),
                y1=float(bbox["y1"]),
            ),
            source=SourceType.OCR,
            confidence=block_data.get("confidence", 0.5),
        )
        blocks.append(block)
    
    # Attempt OMR for note extraction
    omr_result: dict[str, Any] | None = None
    preflight_result: dict[str, Any] | None = None
    
    if run_omr:
        if find_audiveris():
            from src.music.preflight import run_preflight, preflight_to_dict
            
            output_dir = image_path.parent / "omr_output"
            music_dir = image_path.parent / "music"
            
            # Run preflight to check/upscale image
            preflight_data = run_preflight(image_path, staves, music_dir)
            preflight_result = preflight_to_dict(preflight_data)
            
            # Use upscaled image if available, otherwise original
            omr_input_path = preflight_data.upscaled_path or image_path
            
            logger.info(f"OMR input: {omr_input_path}")
            
            omr_data = run_audiveris(omr_input_path, output_dir)
            
            # V10.1: Preflight 2 - Structural anchoring (after OMR parsing)
            structural_hints: dict[str, Any] | None = None
            rhythm_summary: dict[str, Any] | None = None
            
            if omr_data.success and omr_data.measures:
                from src.music.preflight2 import run_preflight2, hints_to_dict
                from src.music.rhythm_normalize import normalize_rhythm, rhythm_to_dict
                
                # Convert measures to dict format for processing
                measures_dict = [
                    {
                        "number": m.number,
                        "key_signature": m.key_signature,
                        "time_signature": m.time_signature,
                        "notes": [
                            {
                                "pitch": n.pitch,
                                "duration": n.duration,
                                "beat": n.beat if hasattr(n, 'beat') else 0.0,
                            }
                            for n in m.notes
                        ],
                    }
                    for m in omr_data.measures
                ]
                
                # Run preflight2 to detect hints and smooth key signatures
                hints = run_preflight2(image, staves, text_blocks, measures_dict)
                structural_hints = hints_to_dict(hints)
                
                # Apply key signature smoothing to OMR data
                if hints.key_signature:
                    for measure in omr_data.measures:
                        if not measure.key_signature:
                            measure.key_signature = hints.key_signature
                
                # Use detected time signature if OMR didn't find one
                if hints.time_signature and not omr_data.time_signature:
                    omr_data.time_signature = hints.time_signature
                    logger.info(f"Applied detected time signature: {hints.time_signature}")
                
                # V10.1: Rhythm normalization
                # Apply time signature to measures that don't have it
                # Use OMR-detected time signature if available, otherwise use hint
                default_time_sig = omr_data.time_signature or hints.time_signature or "4/4"
                
                # Also update preflight2 hints with OMR-detected time signature
                if omr_data.time_signature:
                    structural_hints["time_signature"] = omr_data.time_signature
                    hints.time_signature = omr_data.time_signature
                
                for m_dict in measures_dict:
                    if not m_dict.get("time_signature"):
                        m_dict["time_signature"] = default_time_sig
                    # Also ensure all measures use the detected time signature
                    # (some measures might have different time sigs, but we normalize to first)
                    if m_dict.get("time_signature") != default_time_sig:
                        logger.debug(
                            f"Measure {m_dict.get('number')}: "
                            f"time sig {m_dict.get('time_signature')} -> {default_time_sig}"
                        )
                        m_dict["time_signature"] = default_time_sig
                
                # Normalize rhythm
                normalized_measures = normalize_rhythm(measures_dict)
                rhythm_summary = rhythm_to_dict(normalized_measures)
                
                # Update OMR measures with normalized data
                for i, m in enumerate(omr_data.measures):
                    # Apply time signature to measure
                    if not m.time_signature:
                        m.time_signature = default_time_sig
                    
                    if i < len(normalized_measures):
                        norm_m = normalized_measures[i]
                        # Update note durations and beat positions
                        for j, note in enumerate(m.notes):
                            if j < len(norm_m["notes"]):
                                norm_note = norm_m["notes"][j]
                                note.duration = norm_note["duration"]
                                note.beat = norm_note.get("beat", note.beat)
            
            omr_result = omr_result_to_dict(omr_data)
            
            # Add preflight info to OMR result
            omr_result["preflight"] = preflight_result
            if structural_hints:
                omr_result["preflight2"] = structural_hints
            if rhythm_summary:
                omr_result["rhythm_normalization"] = rhythm_summary

            # Update metadata from OMR if available
            if omr_data.success:
                if omr_data.time_signature:
                    metadata.time_signature = omr_data.time_signature
                if omr_data.key_signature:
                    metadata.key_signature = omr_data.key_signature
                if omr_data.tempo:
                    metadata.tempo = omr_data.tempo
                metadata.measure_count = len(omr_data.measures)
        else:
            omr_result = {
                "success": False,
                "engine": "none",
                "error": "Audiveris not installed. Install for full OMR support.",
                "measure_count": 0,
                "preflight": None,
            }
    
    # Build result
    result = {
        "is_music_sheet": True,
        "confidence": confidence,
        "staff_count": len(staves),
        "metadata": metadata.model_dump(),
        "blocks": [b.model_dump() for b in blocks],
        "detection_info": detection_info,
    }
    
    if omr_result:
        result["omr"] = omr_result
    
    # QA checks
    result["qa"] = run_music_qa(result)
    
    return result


def run_music_qa(result: dict[str, Any]) -> dict[str, Any]:
    """
    Run QA checks on music sheet extraction result.
    
    Returns QA findings with pass/warn/fail status.
    """
    findings: list[dict[str, str]] = []
    status = "pass"
    
    metadata = result.get("metadata", {})
    omr = result.get("omr", {})
    
    # QA 1: Title should be found
    if not metadata.get("title"):
        findings.append({
            "check": "metadata_title",
            "severity": "warning",
            "message": "Title not found in music sheet"
        })
        if status == "pass":
            status = "warning"
    
    # QA 2: Composer should be found
    if not metadata.get("composer"):
        findings.append({
            "check": "metadata_composer",
            "severity": "warning", 
            "message": "Composer not found in music sheet"
        })
        if status == "pass":
            status = "warning"
    
    # QA 3: If OMR ran, measure_count should be > 0
    if omr and omr.get("success") and omr.get("measure_count", 0) == 0:
        findings.append({
            "check": "omr_measures",
            "severity": "warning",
            "message": "OMR succeeded but no measures extracted"
        })
        if status == "pass":
            status = "warning"
    
    # QA 4: If OMR not available, add info
    if omr and not omr.get("success") and omr.get("engine") == "none":
        findings.append({
            "check": "omr_available",
            "severity": "info",
            "message": "Audiveris not installed - no note-level data extracted"
        })
    
    # QA 5: Staff count should match expected (guitar usually 1 staff per system)
    staff_count = result.get("staff_count", 0)
    if staff_count == 0:
        findings.append({
            "check": "staff_detection",
            "severity": "fail",
            "message": "No staff lines detected"
        })
        status = "fail"
    
    # V10.1: QA 6-8 - Rhythm validation
    if omr and omr.get("success") and omr.get("measure_count", 0) > 0:
        rhythm_norm = omr.get("rhythm_normalization", {})
        
        # QA 6: Rhythm normalization status
        if rhythm_norm:
            if not rhythm_norm.get("all_valid", False):
                corrected = rhythm_norm.get("corrected_measures", 0)
                total = rhythm_norm.get("total_measures", 0)
                findings.append({
                    "check": "rhythm_validation",
                    "severity": "warning",
                    "message": f"Rhythm errors in {corrected}/{total} measures (corrected)"
                })
                if status == "pass":
                    status = "warning"
        
        # QA 7: Check for missing time signatures
        measures = omr.get("measures", [])
        measures_without_time = [
            m for m in measures if not m.get("time_signature")
        ]
        if measures_without_time:
            findings.append({
                "check": "time_signature_coverage",
                "severity": "warning",
                "message": f"{len(measures_without_time)} measures without time signature"
            })
            if status == "pass":
                status = "warning"
        
        # QA 8: Check for notes without beat positions
        notes_without_beat = 0
        for measure in measures:
            for note in measure.get("notes", []):
                if note.get("beat") is None or note.get("beat") == 0.0:
                    notes_without_beat += 1
        
        if notes_without_beat > len(measures):  # More than 1 per measure average
            findings.append({
                "check": "beat_positions",
                "severity": "warning",
                "message": f"Many notes ({notes_without_beat}) without beat positions"
            })
            if status == "pass":
                status = "warning"
    
    return {
        "status": status,
        "findings": findings,
        "checks_run": 8,  # Updated from 5
    }


if __name__ == "__main__":
    import json
    import sys
    
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) < 2:
        print("Usage: python extract.py <image_path>")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    result = process_music_sheet(image_path)
    
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
