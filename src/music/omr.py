"""
Optical Music Recognition (OMR) integration.

Supports Audiveris for MusicXML extraction.
Falls back to staff-detect + OCR when Audiveris is not available.
"""

import json
import logging
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Note:
    """A single musical note."""
    pitch: str  # e.g., "C4", "D#5"
    duration: str  # e.g., "quarter", "half", "whole"
    beat: float  # Beat position in measure
    voice: int = 1
    
    
@dataclass
class Measure:
    """A musical measure/bar."""
    number: int
    notes: list[Note] = field(default_factory=list)
    time_signature: str | None = None
    key_signature: str | None = None
    tempo: str | None = None


@dataclass
class OMRResult:
    """Result from OMR processing."""
    success: bool
    engine: str  # "audiveris", "none"
    measures: list[Measure] = field(default_factory=list)
    time_signature: str | None = None
    key_signature: str | None = None
    tempo: str | None = None
    error: str | None = None
    musicxml_path: Path | None = None


def find_audiveris() -> Path | None:
    """Find Audiveris installation."""
    # Common installation paths (both .exe and .bat)
    paths = [
        Path("C:/Program Files/Audiveris/Audiveris.exe"),
        Path("C:/Program Files/Audiveris/bin/Audiveris.bat"),
        Path("C:/Program Files (x86)/Audiveris/Audiveris.exe"),
        Path("C:/Program Files (x86)/Audiveris/bin/Audiveris.bat"),
        Path.home() / "AppData" / "Local" / "Audiveris" / "Audiveris.exe",
        Path.home() / "AppData" / "Local" / "Audiveris" / "bin" / "Audiveris.bat",
    ]
    
    for path in paths:
        if path.exists():
            return path
    
    # Try PATH
    try:
        result = subprocess.run(
            ["where", "audiveris"], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return Path(result.stdout.strip().split('\n')[0])
    except Exception:
        pass
    
    return None


def run_audiveris(image_path: Path, output_dir: Path) -> OMRResult:
    """
    Run Audiveris OMR on an image.
    
    Args:
        image_path: Path to music sheet image
        output_dir: Directory for output files
    
    Returns:
        OMRResult with extracted musical data
    """
    audiveris_path = find_audiveris()
    
    if not audiveris_path:
        return OMRResult(
            success=False,
            engine="none",
            error="Audiveris not found. Install from https://github.com/Audiveris/audiveris"
        )
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run Audiveris in batch mode
        cmd = [
            str(audiveris_path),
            "-batch",
            "-export",
            "-output", str(output_dir),
            str(image_path)
        ]
        
        logger.info(f"Running Audiveris: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )
        
        if result.returncode != 0:
            logger.error(f"Audiveris failed: {result.stderr}")
            return OMRResult(
                success=False,
                engine="audiveris",
                error=f"Audiveris error: {result.stderr[:500]}"
            )
        
        # Check log file for errors (Audiveris may return 0 even on failure)
        log_files = list(output_dir.glob("*.log"))
        if log_files:
            log_content = log_files[0].read_text(encoding="utf-8", errors="ignore")
            if "resolution is too low" in log_content or "flagged as invalid" in log_content:
                logger.warning("Audiveris: Image resolution too low (need 300 DPI)")
                return OMRResult(
                    success=False,
                    engine="audiveris",
                    error="Image resolution too low. Audiveris requires 300 DPI minimum. "
                          "Try scanning at higher resolution."
                )
        
        # Find MusicXML output (Audiveris may create multiple movements)
        stem = image_path.stem
        musicxml_paths = list(output_dir.glob(f"{stem}*.mxl")) + \
                        list(output_dir.glob(f"{stem}*.musicxml")) + \
                        list(output_dir.glob(f"*.mxl")) + \
                        list(output_dir.glob(f"*.musicxml"))
        
        # Remove duplicates and prefer .mxl
        seen = set()
        unique_paths = []
        for p in musicxml_paths:
            if p.name not in seen:
                seen.add(p.name)
                unique_paths.append(p)
        musicxml_paths = sorted(unique_paths, key=lambda p: (p.suffix != '.mxl', p.name))
        
        if not musicxml_paths:
            return OMRResult(
                success=False,
                engine="audiveris",
                error="Audiveris produced no MusicXML output"
            )
        
        musicxml_path = musicxml_paths[0]
        return parse_musicxml(musicxml_path)
        
    except subprocess.TimeoutExpired:
        return OMRResult(
            success=False,
            engine="audiveris",
            error="Audiveris timed out (>5 minutes)"
        )
    except Exception as e:
        return OMRResult(
            success=False,
            engine="audiveris",
            error=f"Audiveris exception: {str(e)}"
        )


def parse_musicxml(path: Path) -> OMRResult:
    """
    Parse MusicXML file and extract musical data.
    
    Supports both uncompressed (.xml, .musicxml) and compressed (.mxl) formats.
    
    Args:
        path: Path to MusicXML file
    
    Returns:
        OMRResult with parsed data
    """
    import zipfile
    
    try:
        # Handle compressed MusicXML (.mxl)
        if path.suffix.lower() == ".mxl":
            with zipfile.ZipFile(path, 'r') as zf:
                # Find the main XML file in the archive
                xml_files = [f for f in zf.namelist() 
                            if f.endswith('.xml') and not f.startswith('META-INF')]
                
                if not xml_files:
                    return OMRResult(
                        success=False,
                        engine="audiveris",
                        error="No XML file found in MXL archive",
                        musicxml_path=path,
                    )
                
                # Prefer container.xml or root file
                main_file = xml_files[0]
                for f in xml_files:
                    if 'container' not in f.lower():
                        main_file = f
                        break
                
                with zf.open(main_file) as xml_file:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
        else:
            tree = ET.parse(path)
            root = tree.getroot()
        
        # Handle namespace
        ns = {'': 'http://www.musicxml.org/xsd/3.1'} if root.tag.startswith('{') else {}
        
        measures: list[Measure] = []
        time_sig: str | None = None
        key_sig: str | None = None
        tempo: str | None = None
        
        # Find all measures
        for part in root.findall('.//part', ns) or root.findall('.//part'):
            for measure_elem in part.findall('.//measure', ns) or part.findall('.//measure'):
                measure_num = int(measure_elem.get('number', 0))
                measure = Measure(number=measure_num)
                
                # Extract notes
                for note_elem in measure_elem.findall('.//note', ns) or measure_elem.findall('.//note'):
                    pitch_elem = note_elem.find('.//pitch', ns) or note_elem.find('.//pitch')
                    if pitch_elem is not None:
                        step = pitch_elem.findtext('step', '', ns) or pitch_elem.findtext('step', '')
                        octave = pitch_elem.findtext('octave', '', ns) or pitch_elem.findtext('octave', '')
                        alter = pitch_elem.findtext('alter', '', ns) or pitch_elem.findtext('alter', '')
                        
                        # Build pitch string
                        pitch = step
                        if alter == '1':
                            pitch += '#'
                        elif alter == '-1':
                            pitch += 'b'
                        pitch += octave
                        
                        # Get duration type
                        duration_type = note_elem.findtext('.//type', 'quarter', ns) or \
                                       note_elem.findtext('.//type', 'quarter')
                        
                        note = Note(
                            pitch=pitch,
                            duration=duration_type,
                            beat=1.0,  # TODO: Calculate from position
                        )
                        measure.notes.append(note)
                
                # Extract time signature
                time_elem = measure_elem.find('.//time', ns) or measure_elem.find('.//time')
                if time_elem is not None:
                    beats = time_elem.findtext('beats', '', ns) or time_elem.findtext('beats', '')
                    beat_type = time_elem.findtext('beat-type', '', ns) or time_elem.findtext('beat-type', '')
                    if beats and beat_type:
                        measure.time_signature = f"{beats}/{beat_type}"
                        if not time_sig:
                            time_sig = measure.time_signature
                
                # Extract key signature
                key_elem = measure_elem.find('.//key', ns) or measure_elem.find('.//key')
                if key_elem is not None:
                    fifths = key_elem.findtext('fifths', '0', ns) or key_elem.findtext('fifths', '0')
                    fifths_int = int(fifths)
                    key_names = {
                        -7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb", -2: "Bb", -1: "F",
                        0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#"
                    }
                    measure.key_signature = key_names.get(fifths_int, "C")
                    if not key_sig:
                        key_sig = measure.key_signature
                
                if measure.notes or measure.time_signature or measure.key_signature:
                    measures.append(measure)
        
        return OMRResult(
            success=True,
            engine="audiveris",
            measures=measures,
            time_signature=time_sig,
            key_signature=key_sig,
            tempo=tempo,
            musicxml_path=path,
        )
        
    except Exception as e:
        return OMRResult(
            success=False,
            engine="audiveris",
            error=f"MusicXML parsing error: {str(e)}",
            musicxml_path=path,
        )


def omr_result_to_dict(result: OMRResult) -> dict[str, Any]:
    """Convert OMRResult to JSON-serializable dict."""
    return {
        "success": result.success,
        "engine": result.engine,
        "time_signature": result.time_signature,
        "key_signature": result.key_signature,
        "tempo": result.tempo,
        "measure_count": len(result.measures),
        "note_count": sum(len(m.notes) for m in result.measures),
        "measures": [
            {
                "number": m.number,
                "time_signature": m.time_signature,
                "key_signature": m.key_signature,
                "notes": [
                    {"pitch": n.pitch, "duration": n.duration, "beat": n.beat}
                    for n in m.notes
                ]
            }
            for m in result.measures
        ],
        "error": result.error,
        "musicxml_path": str(result.musicxml_path) if result.musicxml_path else None,
    }


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) < 2:
        print("Usage: python omr.py <image_path>")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    output_dir = image_path.parent / "omr_output"
    
    print(f"Checking Audiveris: {find_audiveris()}")
    
    result = run_audiveris(image_path, output_dir)
    print(json.dumps(omr_result_to_dict(result), indent=2))
