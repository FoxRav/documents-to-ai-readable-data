#!/usr/bin/env python3
"""
Process any image and output structured data for AI consumption.

Automatically detects content type (music sheet, document, etc.) 
and applies appropriate extraction.

Usage:
    python tools/process_image.py <image_path> [--output json|markdown]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.music.detect import detect_music_sheet_from_path
from src.music.extract import process_music_sheet


def format_as_markdown(result: dict) -> str:
    """Format extraction result as readable Markdown for AI."""
    lines: list[str] = []
    
    if result.get("is_music_sheet"):
        lines.append("# Music Sheet Analysis")
        lines.append("")
        lines.append("## Content Type: MUSIC_SHEET")
        lines.append(f"**Confidence**: {result.get('confidence', 0):.0%}")
        lines.append(f"**Staff Systems**: {result.get('staff_count', 0)}")
        lines.append("")
        
        metadata = result.get("metadata", {})
        
        lines.append("## Metadata")
        if metadata.get("title"):
            lines.append(f"- **Title**: {metadata['title']}")
        if metadata.get("composer"):
            lines.append(f"- **Composer**: {metadata['composer']}")
        if metadata.get("dedication"):
            lines.append(f"- **Dedication**: {metadata['dedication']}")
        if metadata.get("tempo"):
            lines.append(f"- **Tempo**: {metadata['tempo']}")
        if metadata.get("time_signature"):
            lines.append(f"- **Time Signature**: {metadata['time_signature']}")
        if metadata.get("key_signature"):
            lines.append(f"- **Key Signature**: {metadata['key_signature']}")
        if metadata.get("copyright"):
            lines.append(f"- **Copyright**: {metadata['copyright']}")
        if metadata.get("measure_count") and metadata.get("measure_count") > 0:
            lines.append(f"- **Measures**: {metadata['measure_count']}")
        
        lines.append("")
        
        if metadata.get("dynamics"):
            lines.append("## Dynamic Markings")
            lines.append(", ".join(metadata["dynamics"]))
            lines.append("")
        
        if metadata.get("expressions"):
            lines.append("## Expression Markings")
            lines.append(", ".join(metadata["expressions"]))
            lines.append("")
        
        if metadata.get("performance_notes"):
            lines.append("## Performance Notes")
            for note in metadata["performance_notes"]:
                lines.append(f"- {note}")
            lines.append("")
        
        # OMR Results
        omr = result.get("omr", {})
        if omr:
            lines.append("## OMR (Optical Music Recognition)")
            if omr.get("success"):
                lines.append(f"- **Engine**: {omr.get('engine', 'unknown')}")
                lines.append(f"- **Measures**: {omr.get('measure_count', 0)}")
                lines.append(f"- **Notes**: {omr.get('note_count', 0)}")
            else:
                lines.append(f"- **Status**: Not available")
                lines.append(f"- **Reason**: {omr.get('error', 'Unknown')}")
            lines.append("")
        
        # QA Results
        qa = result.get("qa", {})
        if qa:
            lines.append("## QA Check Results")
            lines.append(f"**Status**: {qa.get('status', 'unknown').upper()}")
            for finding in qa.get("findings", []):
                severity = finding.get("severity", "info")
                message = finding.get("message", "")
                icon = {"fail": "[FAIL]", "warning": "[WARN]", "info": "[INFO]"}.get(severity, "-")
                lines.append(f"- {icon} {message}")
            lines.append("")
        
        lines.append("## Extracted Text Blocks")
        for block in result.get("blocks", []):
            block_type = block.get("type", "text")
            text = block.get("text", "")
            lines.append(f"- [{block_type}] {text}")
    
    else:
        lines.append("# Image Analysis")
        lines.append("")
        lines.append("## Content Type: UNKNOWN")
        lines.append("This image was not recognized as a music sheet.")
        lines.append(f"**Detection info**: {result.get('detection_info', {})}")
    
    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process image and extract structured data for AI"
    )
    parser.add_argument("image_path", type=Path, help="Path to image file")
    parser.add_argument(
        "--output", 
        choices=["json", "markdown"], 
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)
    
    if not args.image_path.exists():
        print(f"Error: Image not found: {args.image_path}", file=sys.stderr)
        sys.exit(1)
    
    # Detect content type
    is_music, confidence, detection_info = detect_music_sheet_from_path(args.image_path)
    
    if is_music:
        # Process as music sheet
        result = process_music_sheet(args.image_path)
    else:
        # For now, return detection info for non-music images
        # Future: add other document type processing
        result = {
            "is_music_sheet": False,
            "confidence": confidence,
            "detection_info": detection_info,
            "message": "Image is not a music sheet. Other document types not yet implemented."
        }
    
    # Output
    if args.output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_as_markdown(result))


if __name__ == "__main__":
    main()
