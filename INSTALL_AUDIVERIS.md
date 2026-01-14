# Audiveris OMR Installation Guide

Audiveris is an open-source Optical Music Recognition (OMR) engine that extracts musical notation (notes, measures, time signatures) from sheet music images.

## Why Audiveris?

Without Audiveris, the music sheet pipeline provides:
- Staff line detection
- Text/metadata extraction (title, composer, dynamics)
- OCR for text elements

With Audiveris, you additionally get:
- **Measure extraction** (measure_count > 0)
- **Note-level data** (pitch, duration)
- **Time signature** detection
- **Key signature** detection
- **MusicXML export** for use in music notation software

## Installation

### Windows

1. **Download Audiveris**:
   - Go to [Audiveris Releases](https://github.com/Audiveris/audiveris/releases)
   - Download the latest Windows installer (`.exe` or `.msi`)

2. **Install**:
   - Run the installer
   - Default path: `C:\Program Files\Audiveris\`

3. **Verify**:
   ```powershell
   & "C:\Program Files\Audiveris\bin\Audiveris.bat" -help
   ```

### Alternative: Build from Source

Audiveris requires Java 17+:

```bash
# Clone repository
git clone https://github.com/Audiveris/audiveris.git
cd audiveris

# Build
./gradlew build

# Run
./gradlew run
```

## Configuration

No configuration needed. The pipeline automatically detects Audiveris in:
- `C:\Program Files\Audiveris\bin\Audiveris.bat`
- `C:\Program Files (x86)\Audiveris\bin\Audiveris.bat`
- `%LOCALAPPDATA%\Audiveris\bin\Audiveris.bat`
- System PATH

## Usage

Once installed, run the music sheet pipeline:

```bash
python tools/process_image.py data/00_input/sheet_music.jpg
```

The output will include:
- `omr.success: true`
- `omr.measure_count: N`
- `omr.note_count: N`
- `metadata.time_signature`
- `metadata.key_signature`

## Troubleshooting

### Audiveris not found
```
[INFO] Audiveris not installed - no note-level data extracted
```

**Solution**: Install Audiveris and ensure it's in one of the expected paths.

### OMR timeout
```
Audiveris timed out (>5 minutes)
```

**Solution**: Complex scores may take longer. Try with simpler sheet music first.

### MusicXML parsing error

**Solution**: Some MusicXML variations may not parse correctly. The raw `.musicxml` file is saved in `omr_output/` for manual inspection.

## Resources

- [Audiveris GitHub](https://github.com/Audiveris/audiveris)
- [Audiveris Wiki](https://github.com/Audiveris/audiveris/wiki)
- [MusicXML Standard](https://www.musicxml.com/)
