# Definition of Done (DoD)

## Financial Statement Pipeline

### Data Extraction
- [ ] Full-run 150-200 pages completes successfully
- [ ] `document.json` is not empty
- [ ] All pages have content (items > 0)

### TOC Processing
- [ ] TOC pages detected and classified
- [ ] TOC entries parsed with target page numbers
- [ ] Offset mapping (document page → PDF index) works

### Semantic Classification
- [ ] `financial_type` identifies:
  - [ ] `income_statement`
  - [ ] `balance_sheet`
  - [ ] `cash_flow_statement`
  - [ ] `notes`

### QA Checkers
- [ ] OCRQualityChecker: Reports bad% and warnings
- [ ] SemanticSectionChecker: Validates page classifications
- [ ] BalanceSheetEquationChecker: Assets ≈ Liabilities + Equity
- [ ] SumConsistencyChecker: Sub-items sum to totals
- [ ] CrossRefChecker: Note references exist
- [ ] DiffChecker: Regression against golden file

### Quality Gates
- [ ] OCR bad% < 20% (lenient)
- [ ] OCR bad% < 10% (strict)
- [ ] No empty pages on content sections

---

## Music Sheet Pipeline

### V9: Detection & Routing (COMPLETE)
- [x] `is_music_sheet = true` for valid music sheets
- [x] Staff line detection (≥3 staves)
- [x] Confidence score > 0.5
- [x] Staff masking before text OCR
- [x] Noise filtering (confidence + whitelist)

### V9: Output Files
- [x] `music/music.json` - Structured data
- [x] `music/music.md` - Human-readable
- [ ] `music/music.xml` - MusicXML (requires Audiveris)

### V9: Metadata Extraction
- [x] Title detected
- [x] Composer detected
- [x] Dedication detected (if present)
- [x] Dynamic markings (p, mf, f, etc.)
- [ ] Time signature (requires OMR)
- [ ] Key signature (requires OMR)

### V10: OMR Production (COMPLETE)
- [x] Audiveris installed and working
- [x] `omr.success = true`
- [x] `measure_count > 0`
- [x] Note-level data extracted (pitch, duration)
- [x] MusicXML generated
- [x] Preflight upscaling (interline-based)
- [x] Time/key signature extraction
- [ ] Measure duration = time signature (validation) ⚠️ Partial (rhythm errors present)

### V10: QA Checks
- [x] Staff detection passes
- [x] Metadata found (title OR composer)
- [x] OMR success when Audiveris installed
- [x] measure_count > 0
- [ ] No ERROR-level findings ⚠️ Rhythm errors present (expected for V10)

### V10: Final DoD (Music Sheet) - Status
```
✅ is_music_sheet = true
✅ omr.success = true
✅ measure_count > 0
✅ music.json contains measures[].notes[]
✅ Each note: pitch + duration
⚠️ Each note: beat_position (partial - rhythm errors)
✅ Metadata: title + composer
⚠️ QA status = PASS (with rhythm warnings)
✅ music.xml generated
```

**V10 Status:** Technical OMR complete, rhythm semantics partial (V10.1 planned)

---

### V10.1: Rhythm Semantics (PLANNED)

### V10.1: Preflight 2 - Structural Anchoring
- [ ] Time signature hint detection/assignment
- [ ] Clef hint detection/assignment
- [ ] Key signature smoothing across measures
- [ ] Hints passed to Audiveris

### V10.1: Post-Processing - Rhythm Normalization
- [ ] Measure duration validation
- [ ] Voice excess correction (merge/split/normalize)
- [ ] Time offset reconstruction
- [ ] Beat position normalization

### V10.1: QA v2 - Rhythm Validation
- [ ] Rhythm quality checks implemented
- [ ] Duration mismatch detection
- [ ] Overlapping notes detection
- [ ] QA status = PASS (no rhythm errors)

### V10.1: Final DoD (Music Sheet)
```
✅ is_music_sheet = true
✅ omr.success = true
✅ measure_count > 0
✅ music.json contains measures[].notes[]
✅ Each note: pitch + duration + beat_position (corrected)
✅ Measure duration = time signature (validated)
✅ Metadata: title + composer
✅ QA status = PASS (no rhythm errors)
✅ music.xml generated
```

---

## General Quality Standards

### Code Quality
- [ ] Type hints on all functions
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] No hardcoded secrets

### Documentation
- [x] README.md complete
- [x] PROJECT.md overview
- [x] Installation guides
- [ ] API documentation

### Testing
- [ ] Unit tests for core functions
- [ ] Integration tests for pipeline
- [ ] Golden file regression tests
