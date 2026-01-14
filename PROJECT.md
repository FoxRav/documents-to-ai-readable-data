# KuntaParse / PDF-tyyppireititin

Production-ready document and image parsing pipeline that produces **near 100% accurate** structured data (JSON + Markdown) from complex documents.

## Supported Inputs

| Type | Description | Status |
|------|-------------|--------|
| **Digital PDF** | Native text + tables | ✅ V1-V8 |
| **Scanned PDF** | OCR + adaptive PSM + tables | ✅ V1-V8 |
| **Document Image** | JPG/PNG → OCR | ⏳ Planned |
| **Music Sheet Image** | JPG/PNG → OMR → MusicXML | ✅ V9 |

## Quick Start

### PDF Processing
```bash
python -m src.pipeline.run_all --pdf data/00_input/document.pdf
```

### Image Processing (Music Sheet)
```bash
python -m src.pipeline.run_all --image data/00_input/sheet_music.jpg
```

## Target Use Cases

1. **Municipal Financial Statements** (150-200 pages)
   - Tables, text, appendices
   - Balance sheet, income statement, cash flow
   - TOC-guided navigation

2. **Music Sheet Digitization**
   - Staff detection + OMR
   - Metadata extraction (title, composer)
   - MusicXML export

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     ROUTER                              │
│  Detects: digital_pdf / scanned_pdf / image_music /    │
│           image_document                                │
└─────────────────┬───────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    ▼             ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│Digital │  │ Scanned  │  │  Image   │  │  Music   │
│  PDF   │  │   PDF    │  │   Doc    │  │  Sheet   │
└────┬───┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │           │             │             │
     ▼           ▼             ▼             ▼
  Native     Render +       OCR +        Staff +
  Text +     OCR +         Layout        OMR +
  Tables     Adaptive                    Metadata
             PSM
     │           │             │             │
     └───────────┴──────┬──────┴─────────────┘
                        ▼
                 ┌──────────────┐
                 │   Merge &    │
                 │   Classify   │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │     QA       │
                 │   Checks     │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │   Export     │
                 │  JSON / MD   │
                 └──────────────┘
```

## Core Principles

### 1. No Empty Data Rule
Empty `document.json` = failed run, even if pipeline doesn't crash.

### 2. Gate Development (Iterative)
Each version adds one "gate" level success criterion:
1. First data → then semantics → then QA → then optimization

### 3. Reliability
- Fallbacks are mandatory (empty result = fallback or FAIL)
- All important decisions are logged and auditable

## Version History

| Version | Focus | Key Features |
|---------|-------|--------------|
| V1 | Base structure | Steps 00-70 |
| V2 | Empty data fix | Step 41B mandatory |
| V3 | Re-run + verify | Verification scripts |
| V4 | OCR stabilization | PaddleOCR fail handling |
| V5 | Tesseract primary | PaddleOCR isolation |
| V6 | OCR quality | Semantic classification |
| V7 | TOC modeling | OCR quality gate |
| V8 | Adaptive PSM | TOC→target pages, QA |
| V9 | Music sheets | Staff detection, metadata extraction |
| V10 | OMR production | Audiveris integration, preflight upscaling, MusicXML parsing |
| V10.1 | Rhythm semantics | Preflight 2 (anchoring), post-processing (normalization) |

## Documentation

- `README.md` - Installation and usage
- `docs/roadmap.md` - Development roadmap
- `docs/dod.md` - Definition of Done
- `INSTALL_TESSERACT.md` - Tesseract OCR setup
- `INSTALL_AUDIVERIS.md` - Audiveris OMR setup

## Next Steps

### PDF Pipeline
1. Full-run 154 pages + quality gate (bad% < 10-20%)
2. TOC offset mapping reliable
3. Golden file + DiffChecker regression

### Music Sheet Pipeline (V10.1)
1. ✅ Audiveris installation + testing (V10 complete)
2. ✅ MusicXML parsing (V10 complete)
3. ⏳ Rhythm semantics normalization (V10.1 planned)
   - Preflight 2: Time/clef/key anchoring
   - Post-processing: Voice excess correction
   - QA v2: Rhythm validation
4. Future: Multi-page sheet music support
