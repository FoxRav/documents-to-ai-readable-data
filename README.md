# Documents to AI-Readable Data

Production-ready document and image parsing pipeline that converts PDFs and images (JPG/PNG) into structured, AI-readable data (JSON + Markdown).

**Status (V10):** Full pipeline supporting:
- **PDF Processing** (V1-V8): Digital, scanned, and mixed PDFs with adaptive OCR
- **Image Processing** (V9-V10): Music sheet OMR (Optical Music Recognition) and document image OCR

See `PROJECT.md` for roadmap.

## Core Logic: How the Pipeline Works

### 1. Router (Content Type Detection)

The pipeline first determines the **input type** and routes to the appropriate processing path:

```
Input File
    │
    ├─→ PDF? ──→ PDF Router (Step 00)
    │              ├─→ Digital PDF (native text)
    │              ├─→ Scanned PDF (OCR required)
    │              └─→ Mixed PDF (hybrid approach)
    │
    └─→ Image (JPG/PNG)? ──→ Image Router
                                 ├─→ Music Sheet? ──→ OMR Pipeline
                                 │     (staff detection)
                                 │
                                 └─→ Document Image ──→ OCR Pipeline
                                       (general text)
```

**Router Decision Logic:**
- **PDF**: File extension `.pdf` → PDF pipeline
- **Image**: File extension `.jpg`, `.jpeg`, `.png` → Image router
  - **Music Sheet**: Staff line detection (≥3 staves) → OMR path
  - **Document**: No staff lines → OCR path

### 2. PDF Pipeline Logic (Steps 00-70)

#### Step 00: Probe & Route (Page Classification)

Each PDF page is classified as:
- **`digital`**: Contains native text (extractable via PyMuPDF)
- **`scan`**: No native text, requires OCR
- **`mixed`**: Both native text and scanned regions

**Classification Logic:**
```python
if page.has_text and text_ratio > 0.1:
    mode = "digital"  # Use native text extraction
elif page.has_images and image_area > 0.5:
    mode = "scan"    # Requires full OCR
else:
    mode = "mixed"   # Hybrid: native + OCR for images
```

#### Steps 10-41: Extraction Phase

**Digital Path:**
1. Extract native text blocks (PyMuPDF)
2. Extract vector tables (Camelot/Tabula)
3. Minimal OCR only for image regions

**Scan Path:**
1. Render page to PNG (300 DPI)
2. Detect layout regions (text, tables, images)
3. **Adaptive OCR** (V8):
   - Pass 1: Default PSM (6)
   - Pass 2: PSM=11 (sparse text) if quality "bad"
   - Pass 3: PSM=3 (auto) + aggressive preprocessing
   - Pass 4: PSM=4 (single column) + aggressive preprocessing
   - Select best pass based on quality metrics

**Quality Metrics:**
- `alpha_ratio`: Ratio of alphabetic characters
- `digit_ratio`: Ratio of digits
- `repeat_run_max`: Maximum repeated character runs (noise indicator)
- `junk_token_ratio`: Ratio of invalid tokens
- **Status**: "good" / "bad" based on thresholds

#### Step 55: Semantic Classification

**Two-Pass Classification:**

1. **First Pass**: Initial page classification
   - Detect TOC pages (table → list_item conversion)
   - Basic section detection

2. **TOC-Guided Mapping:**
   - Calculate `page_number_offset` (document page → PDF index)
   - Build `toc_target_map` from TOC entries
   - Map `toc_target_page` → `pdf_target_page`

3. **Second Pass**: Refined classification
   - TOC targets: Use TOC-derived `financial_type`
   - Hard rules: Keyword-based detection (Finnish/English)
   - Fallback: Generic section classification

**Financial Statement Detection:**
```python
# Hard rules (V8)
if "VASTAAVAA" in text and "VASTATTAVAA" in text:
    financial_type = "balance_sheet"
elif "TOIMINTATUOTOT" in text or "REVENUE" in text:
    financial_type = "income_statement"
# ... etc
```

#### Step 60: QA Validation

**QA Checkers:**
- `OCRQualityChecker`: Bad% threshold (10% strict, 20% lenient)
- `SemanticSectionChecker`: Page classification validation
- `BalanceSheetEquationChecker`: Assets ≈ Liabilities + Equity
- `SumConsistencyChecker`: Sub-items sum to totals
- `CrossRefChecker`: Note references exist
- `DiffChecker`: Regression against golden file

### 3. Music Sheet Pipeline Logic (V9-V10)

#### Detection Phase

1. **Staff Line Detection** (`src/music/detect.py`):
   - Horizontal line detection (morphology)
   - Group into staves (5 lines per staff)
   - Calculate `line_spacing` (interline in pixels)
   - **Threshold**: ≥3 staves → `is_music_sheet = true`

2. **Text Extraction** (with staff masking):
   - **Header region**: Title, composer, dedication
   - **Footer region**: Copyright
   - **Between staves**: Dynamics, expressions
   - **Staff areas masked**: Prevents OCR noise from notation

#### OMR Preflight (V10)

**Automatic Image Upscaling:**

```python
detected_interline = median(staff.line_spacing)  # e.g., 5.0 px
if detected_interline < MIN_INTERLINE_PX (12px):
    scale_factor = TARGET_INTERLINE_PX (20px) / detected_interline
    # e.g., 20 / 5 = 4.0x upscale
    upscaled_image = cv2.resize(image, scale_factor=4.0)
```

**Why?** Audiveris requires sufficient pixel resolution. Low interline = low DPI = OMR failure.

**Preflight Output:**
- `detected_interline_px`: Original interline
- `scale_factor`: Applied upscale (1.0 = no change)
- `upscaled_path`: Path to upscaled image
- `original_size` / `upscaled_size`: Dimensions

#### OMR Processing (Audiveris)

1. **Input**: Upscaled image (or original if interline ≥ 12px)
2. **Audiveris CLI**: `-batch -export -output <dir> <image>`
3. **Output**: MusicXML files (`.mxl` = compressed, `.xml` = uncompressed)
4. **Parsing**: Extract measures, notes, time/key signatures

**Current Limitations (V10):**
- ✅ Symbol recognition: **Works** (notes, clefs, time signatures detected)
- ⚠️ Rhythm semantics: **Partial** (time offset errors, voice excess warnings)
- **Root Cause**: Audiveris struggles with rhythm inference on scanned material without strong temporal anchors

#### Post-Processing (V10.1 - Planned)

**Rhythm Normalization:**
- Calculate measure duration from notes
- Validate against time signature
- Auto-correct "voice excess" errors
- Normalize beat positions

### 4. Output Structure

**PDF Output:**
```
out/
├── document.json      # Full structured data
├── document.md        # Human-readable
└── qa_report.json     # QA findings
```

**Music Sheet Output:**
```
<input_dir>/music/
├── music.json         # Structured data (measures, notes, metadata)
├── music.md           # AI-readable summary
├── music.xml          # MusicXML (from Audiveris)
└── debug/
    └── omr_input_upscaled.png  # Preflight upscaled image
```

### 5. Error Handling & Fallbacks

**Core Principle**: Empty output = FAIL (not acceptable)

**Fallback Chain:**
1. **Primary method** (e.g., native text extraction)
2. **Fallback method** (e.g., OCR if native fails)
3. **Error logging** + clear failure message

**Example (OCR):**
```python
if primary_ocr.blocks == 0:
    logger.warning("Primary OCR returned 0 blocks, trying fallback")
    fallback_ocr.run()
    if fallback_ocr.blocks == 0:
        raise PipelineError("All OCR methods failed")
```

### 6. Quality Gates

**PDF Pipeline:**
- OCR bad% < 20% (lenient) / < 10% (strict)
- All pages have content (items > 0)
- TOC mapping successful (if TOC present)

**Music Sheet Pipeline:**
- `is_music_sheet = true` (staff detection)
- `measure_count > 0` (OMR success)
- Metadata present (title OR composer)
- QA status = PASS (no errors)

**Current State (V10):**
- ✅ Technical OMR: **Complete** (measures extracted)
- ⚠️ Semantic OMR: **Partial** (rhythm errors present, V10.1 planned)

## Features

### PDF Processing
- **Page-level classification**: Automatically detects if pages are digital, scanned, or mixed
- **Digital-first path**: Native text extraction + vector tables (Camelot/Tabula) + minimal OCR
- **Scan-first path**: Rendering + layout/regions + OCR (region-wise) + table cell structure
- **Adaptive OCR**: Multi-pass OCR with quality-based PSM selection
- **Semantic classification**: Identifies financial statement types (balance sheet, income statement, etc.)

### Image Processing
- **Music sheet recognition**: Automatic staff line detection (≥3 staves) → OMR pipeline
- **OMR processing**: Full Optical Music Recognition with Audiveris (measures, notes, time/key signatures)
- **Document image OCR**: General text extraction from JPG/PNG images
- **Automatic upscaling**: Image quality enhancement for low-resolution music sheets

### General
- **QA checks**: Sum consistency, balance checks, cross-references, and more
- **Export formats**: JSON (structured) and Markdown (human-readable)
- **Multi-format support**: PDF, JPG, PNG input formats

## Installation

### System Dependencies

- **Tesseract OCR** (REQUIRED for PDF/document image processing): Download from [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Windows installer)
  - Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
  - Verify installation: `tesseract --version`
  - **See `INSTALL_TESSERACT.md` for detailed installation instructions**
- **Poppler** (for PDF rendering): Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases) (Windows)
- **Audiveris** (REQUIRED for music sheet OMR): See `INSTALL_AUDIVERIS.md` for installation instructions

### Python Dependencies

Install using pip or uv:

```bash
# Core dependencies
pip install -e .

# Optional: Tables
pip install -e ".[tables]"

# Optional: OCR
pip install -e ".[ocr]"

# Optional: MinerU
pip install -e ".[mineru]"

# Optional: GPU support
pip install -e ".[gpu]"
```

## Configuration

**`.env` file is already created** in the project root. Edit it to set:

- **TESSERACT_CMD** (REQUIRED): Path to Tesseract executable
  ```
  TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
  ```
- **OCR_PRIMARY**: Primary OCR engine (`tesseract` or `paddle`, default: `tesseract`)
- **OCR_FALLBACK**: Fallback OCR engine (`tesseract`, `paddle`, or `none`, default: `none`)
- Model and cache directories
- Poppler path (Windows)
- GPU settings
- Logging configuration

**Note (V5):** Tesseract is the primary OCR engine. PaddleOCR is optional and isolated (may have compatibility issues).

**✅ Tesseract OCR:** Already installed (v5.4.0.20240606) via winget

## Usage

### Quick Start

#### PDF Processing

1. **✅ Tesseract OCR:** Already installed
2. **✅ `.env` file:** Already created
3. **Place PDF in `data/00_input/`**
4. **Run pipeline:**

```bash
# Prepare assets (first time only)
python -m src.pipeline.run_all --pdf data/00_input/your_file.pdf --prepare-assets

# Run pipeline
python -m src.pipeline.run_all --pdf data/00_input/your_file.pdf
```

#### Image Processing (Music Sheet or Document)

1. **✅ Tesseract OCR:** Already installed (for document images)
2. **✅ Audiveris:** Installed (for music sheet OMR) - See `INSTALL_AUDIVERIS.md`
3. **Place image (JPG/PNG) in `data/00_input/`**
4. **Run pipeline:**

```bash
# Process music sheet image (OMR)
python -m src.pipeline.run_all --image data/00_input/sheet_music.jpg

# Process document image (OCR)
python -m src.pipeline.run_all --image data/00_input/document.jpg
```

### Verification After Run

Check that pipeline produced data:
```powershell
# Check OCR blocks
Get-ChildItem "data\10_work\blocks_ocr\*.jsonl" | Where-Object { (Get-Content $_.FullName -Raw).Length -gt 0 } | Measure-Object

# Check document.json
python -c "import json; d=json.load(open('out/document.json')); print(f'Pages: {len(d[\"pages\"])}, Total items: {sum(len(p.get(\"items\", [])) for p in d[\"pages\"])}')"
```

**Quick links:**
- `QUICK_START.md` - Quick start guide (4 steps)
- `RESTART_GUIDE.md` - Detailed restart instructions
- `INSTALL_TESSERACT.md` - Tesseract OCR installation guide
- `SETUP_CHECKLIST.md` - Setup and verification checklist

### Advanced Options

```bash
python -m src.pipeline.run_all \
  --pdf data/00_input/your_file.pdf \
  --model-dir ./models \
  --cache-dir ./cache \
  --work-dir data/10_work \
  --out-dir out \
  --log-level INFO \
  --log-format json
```

### Music Sheet Processing

Process music sheet images with full OMR (Optical Music Recognition):

```bash
# Unified CLI (recommended)
python -m src.pipeline.run_all --image data/00_input/sheet_music.jpg

# Legacy tool (still works)
python tools/process_image.py data/00_input/sheet_music.jpg --output json
```

**Processing Flow:**
1. **Detection**: Staff line detection (≥3 staves) → `is_music_sheet = true`
2. **Preflight**: Automatic upscaling if interline < 12px
3. **OMR**: Audiveris extracts measures and notes → MusicXML
4. **Parsing**: MusicXML → JSON (measures, notes, time/key signatures)
5. **Metadata**: OCR for title, composer, dynamics (staff areas masked)

**Extracted Data:**
- **Metadata**: Title, composer, dedication, copyright
- **Musical Structure**: Measures, notes (pitch, duration), time/key signatures
- **Markings**: Dynamic markings (p, mf, f, ff), expression markings
- **Staff Info**: Staff count, line positions, interline measurements

**Requirements:**
- **Audiveris** (required for OMR): See `INSTALL_AUDIVERIS.md`
- **Image Quality**: Minimum 12px interline (auto-upscaled if lower)

**Output Location:**
- Output saved to same directory as input: `<input_dir>/music/`
- Files: `music.json`, `music.md`, `music.xml`, `debug/omr_input_upscaled.png`

## Output

The pipeline produces:

- `out/document.json` - Structured document data
- `out/document.md` - Human-readable Markdown export
- `out/qa_report.json` - QA findings and metrics
- `data/10_work/` - Intermediate files (manifests, rendered pages, regions, etc.)

## Pipeline Steps

1. **Step 00**: PDF Probe & Route (page classification)
2. **Step 10**: Native text extraction
3. **Step 20**: Render pages (for scan/mixed)
4. **Step 30**: Layout region detection
5. **Step 40**: Vector table extraction
6. **Step 41**: OCR text and table extraction (Tesseract primary, PaddleOCR optional)
7. **Step 50**: Merge & Reading Order
8. **Step 55**: Semantic classification
9. **Step 60**: Normalize & Validate
10. **Step 70**: Export to Markdown

## Project Structure

```
.
├── src/
│   ├── pipeline/          # Pipeline steps
│   └── schemas/           # JSON schemas and Pydantic models
├── checkers/              # Modular QA checkers
├── tools/                 # Utility scripts
├── data/
│   ├── 00_input/          # Input PDFs
│   └── 10_work/           # Intermediate files
├── out/                   # Final outputs
├── models/                # Model files
└── cache/                 # Cache files
```

## Development

### Code Style

- Type hints required (mypy --strict)
- Black for formatting
- Ruff for linting
- Pydantic for data validation

### Testing

```bash
# Run tests (when implemented)
pytest

# Type checking
mypy src/

# Linting
ruff check src/

# OCR smoke test
python tools/ocr_smoke_test.py data/10_work/pages_png/page_0000.png
```

## Current Status (V10)

### PDF Pipeline (V1-V8)
- ✅ **OCR Strategy**: Tesseract is primary OCR engine
- ✅ **Adaptive PSM**: Multi-pass OCR with quality-based selection (V8)
- ✅ **Fallback Logic**: Automatic fallback if primary OCR returns 0 blocks
- ✅ **TOC Processing**: TOC detection, target page mapping, offset calculation
- ✅ **Semantic Classification**: Financial statement types, TOC-guided routing
- ✅ **QA Checkers**: OCR quality, semantic sections, balance sheet, sums, cross-refs
- ⚠️ **PaddleOCR**: Isolated as optional (may have OneDnnContext compatibility issues)

### Music Sheet Pipeline (V9-V10)
- ✅ **Staff Detection**: Automatic staff line detection (≥3 staves)
- ✅ **OMR Preflight**: Automatic image upscaling (interline-based)
- ✅ **Audiveris Integration**: Full OMR processing (measures, notes extraction)
- ✅ **MusicXML Parsing**: Compressed (.mxl) and uncompressed (.xml) support
- ✅ **Metadata Extraction**: Title, composer, dynamics (with staff masking)
- ⚠️ **Rhythm Semantics**: Partial (time offset errors, V10.1 planned for normalization)

### Known Limitations
- **Music Sheet Rhythm**: Audiveris may produce rhythm errors on scanned material (systematic "voice excess", "no timeOffset" warnings). This is expected for V10 and will be addressed in V10.1 with post-processing normalization.

**Documentation:**
- `PROJECT.md` - Project overview and roadmap
- `docs/roadmap.md` - Version history (V1-V10)
- `docs/dod.md` - Definition of Done
- `INSTALL_TESSERACT.md` - Tesseract OCR installation
- `INSTALL_AUDIVERIS.md` - Audiveris OMR installation
- `QUICK_START.md` - Quick start guide
- `RESTART_GUIDE.md` - Restart instructions
- `LOC_COUNTER.md` - LOC counter tool usage guide

## Troubleshooting

### Tesseract Not Found
```
Error: tesseract is not installed or it's not in your PATH
```
**Solution:** Install Tesseract OCR and set `TESSERACT_CMD` in `.env`

### OCR Returns 0 Blocks
Check logs for OCR errors. Verify:
1. Tesseract is installed: `tesseract --version`
2. `.env` has correct `TESSERACT_CMD` path
3. Rendered PNG images exist in `data/10_work/pages_png/`

### Document.json is Empty
Pipeline will fail with clear error message. Check:
1. `blocks_ocr/` directory contains data
2. OCR logs for errors
3. Tesseract installation

See `RESTART_GUIDE.md` for more troubleshooting.

## License

MIT License - See LICENSE file for details
