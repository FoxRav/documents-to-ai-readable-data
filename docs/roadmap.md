# Development Roadmap

## Version History

### V1: Base Structure
- Pipeline steps 00-70 implemented
- Basic PDF processing flow
- JSON/Markdown export

### V2: Empty Data Fix
- Step 41B (OCR) made mandatory
- Validation for non-empty output

### V3: Re-run & Verification
- Verification scripts added
- Pipeline restart guide

### V4: OCR Stabilization
- PaddleOCR failure handling
- Timeout management
- Fallback logic

### V5: Tesseract Primary
- Tesseract OCR as primary engine
- PaddleOCR isolated as optional
- Installation documentation

### V6: OCR Quality Enhancement
- Image preprocessing (grayscale, threshold, denoise, deskew)
- Quality metrics (alpha_ratio, digit_ratio, junk_token_ratio)
- Semantic classification (page-level)

### V7: TOC Modeling
- TOC detection and list_item modeling
- OCR quality gate (bad% threshold)
- Minimum QA checkers

### V8: Adaptive PSM
- Multi-pass OCR with adaptive PSM selection
- TOC → target page mapping
- Advanced QA checkers:
  - BalanceSheetEquationChecker
  - SumConsistencyChecker
  - CrossRefChecker
  - DiffChecker

### V9: Music Sheet Support
- Staff line detection
- Music sheet routing
- Metadata extraction
- Unified CLI (--pdf / --image)

### V10: OMR Production (Complete)
- OMR integration (Audiveris)
- Preflight upscaling (interline-based)
- MusicXML → JSON parsing
- Measure and note extraction
- Time/key signature detection
- ⚠️ Rhythm semantics partial (rhythm errors present)

### V10.1: Rhythm Semantics (Planned)
- Preflight 2: Time/clef/key anchoring
- Post-processing: Rhythm normalization
- Voice excess correction
- QA v2: Rhythm validation

## Planned Features

### V11: PDF Full Production
- Full 154-page financial statement run
- Quality gate enforcement (bad% < 10%)
- Golden file regression testing
- Performance optimization

### V11: General Images
- Document image OCR (non-music)
- Layout analysis for images
- Multi-page image processing

### V12: Cloud Deployment
- Docker containerization
- API endpoints
- Batch processing
