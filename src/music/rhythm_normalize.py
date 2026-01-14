"""
Rhythm Normalization: Post-processing to correct OMR rhythm errors.

Fixes:
- Voice excess (notes exceeding measure duration)
- Missing time offsets
- Measure duration mismatches
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Duration type to beats mapping
DURATION_BEATS = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "16th": 0.25,
    "32nd": 0.125,
    "64th": 0.0625,
    "breve": 8.0,
    "long": 16.0,
}


def parse_time_signature(time_sig: str | None) -> float:
    """
    Parse time signature to expected beats per measure.
    
    Args:
        time_sig: Time signature string (e.g., "4/4", "6/8", "C")
    
    Returns:
        Expected beats per measure (e.g., 4.0 for 4/4)
    """
    if not time_sig:
        return 4.0  # Default to 4/4
    
    # Common time
    if time_sig.upper() == "C":
        return 4.0
    
    # Cut time
    if time_sig.upper() == "C|":
        return 2.0
    
    # Numeric (e.g., "4/4", "6/8")
    parts = time_sig.split("/")
    if len(parts) == 2:
        try:
            numerator = float(parts[0])
            denominator = float(parts[1])
            # For compound time (6/8, 9/8), beats = numerator / (denominator / 4)
            # For simple time (4/4, 3/4), beats = numerator
            if denominator == 8 and numerator % 3 == 0:
                # Compound time: 6/8 = 2 beats, 9/8 = 3 beats
                return numerator / 3
            else:
                # Simple time: 4/4 = 4 beats, 3/4 = 3 beats
                return numerator
        except ValueError:
            pass
    
    return 4.0  # Default fallback


def duration_to_beats(duration: str) -> float:
    """
    Convert duration type to beats.
    
    Args:
        duration: Duration type (e.g., "quarter", "half")
    
    Returns:
        Beats (e.g., 1.0 for quarter, 2.0 for half)
    """
    duration_lower = duration.lower()
    return DURATION_BEATS.get(duration_lower, 1.0)  # Default to quarter


def validate_measure_duration(
    measure: dict[str, Any],
) -> tuple[bool, float, float]:
    """
    Validate measure duration against time signature.
    
    Args:
        measure: Measure dict with notes and time_signature
    
    Returns:
        (is_valid, expected_beats, actual_beats)
    """
    time_sig = measure.get("time_signature")
    expected = parse_time_signature(time_sig)
    
    notes = measure.get("notes", [])
    actual = sum(duration_to_beats(n.get("duration", "quarter")) for n in notes)
    
    # Allow small tolerance (0.1 beats)
    is_valid = abs(expected - actual) < 0.1
    
    return (is_valid, expected, actual)


def reconstruct_time_offsets(measure: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate beat positions for notes without timeOffset.
    
    Args:
        measure: Measure dict with notes
    
    Returns:
        Measure with beat positions added
    """
    notes = measure.get("notes", [])
    if not notes:
        return measure
    
    current_beat = 0.0
    
    for note in notes:
        # Recalculate beat position
        # OMR often sets beat=1.0 as default, so we recalculate from start
        note["beat"] = current_beat
        
        # Advance by note duration
        duration = duration_to_beats(note.get("duration", "quarter"))
        current_beat += duration
    
    measure["notes"] = notes
    return measure


def correct_voice_excess(measure: dict[str, Any]) -> dict[str, Any]:
    """
    Correct "voice excess" errors by normalizing note durations.
    
    Strategies:
    1. If total duration > time signature, reduce note durations proportionally
    2. If notes overlap, adjust beat positions
    3. Split long notes at measure boundaries
    
    Args:
        measure: Measure dict with notes and time_signature
    
    Returns:
        Corrected measure
    """
    time_sig = measure.get("time_signature")
    expected_beats = parse_time_signature(time_sig)
    
    notes = measure.get("notes", [])
    if not notes:
        return measure
    
    # Calculate total duration
    total_beats = sum(duration_to_beats(n.get("duration", "quarter")) for n in notes)
    
    # If excess, normalize proportionally
    if total_beats > expected_beats + 0.1:  # Small tolerance
        scale_factor = expected_beats / total_beats
        
        logger.debug(
            f"Measure {measure.get('number')}: voice excess "
            f"({total_beats:.2f} > {expected_beats:.2f}), scaling by {scale_factor:.2f}"
        )
        
        # Adjust durations (simplified: reduce proportionally)
        # In practice, this might require more sophisticated note splitting
        for note in notes:
            current_duration = duration_to_beats(note.get("duration", "quarter"))
            new_duration = current_duration * scale_factor
            
            # Find closest standard duration
            closest_duration = min(
                DURATION_BEATS.items(),
                key=lambda x: abs(x[1] - new_duration)
            )
            note["duration"] = closest_duration[0]
    
    # Reconstruct beat positions after duration changes
    measure = reconstruct_time_offsets(measure)
    
    return measure


def normalize_rhythm(measures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize rhythm for all measures.
    
    Args:
        measures: List of measure dicts
    
    Returns:
        Normalized measures
    """
    normalized = []
    
    for measure in measures:
        # Reconstruct time offsets
        measure = reconstruct_time_offsets(measure)
        
        # Correct voice excess
        measure = correct_voice_excess(measure)
        
        # Validate
        is_valid, expected, actual = validate_measure_duration(measure)
        if not is_valid:
            logger.warning(
                f"Measure {measure.get('number')}: duration mismatch "
                f"(expected {expected:.2f}, got {actual:.2f})"
            )
        
        normalized.append(measure)
    
    return normalized


def rhythm_to_dict(measures: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert normalized measures to summary dict."""
    total_measures = len(measures)
    corrected_count = 0
    errors: list[str] = []
    
    for measure in measures:
        is_valid, expected, actual = validate_measure_duration(measure)
        if not is_valid:
            corrected_count += 1
            errors.append(
                f"Measure {measure.get('number')}: {actual:.2f}/{expected:.2f} beats"
            )
    
    return {
        "total_measures": total_measures,
        "corrected_measures": corrected_count,
        "errors": errors,
        "all_valid": corrected_count == 0,
    }
