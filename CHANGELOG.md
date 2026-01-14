# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-10

### Added
- Full pipeline implementation (Steps 00-70)
- Page-level classification (digital/scanned/mixed)
- Native text extraction for digital pages
- OCR text extraction using Tesseract OCR (primary engine)
- Vector table extraction (Camelot/Tabula)
- Layout region detection
- Reading order reconstruction
- Semantic classification for financial statements
- Basic QA checkers (SchemaChecker, SumChecker)
- Export to JSON and Markdown formats
- GPU support for OCR operations
- Fallback logic for OCR engines

### Changed
- V5: Tesseract OCR as primary OCR engine (PaddleOCR isolated as optional)
- V4: Attempted PaddleOCR stabilization (failed due to OneDnnContext issues)
- V3: Added OCR text extraction for scan pages
- V2: Fixed empty document.json issue

### Fixed
- Empty document.json issue (V2)
- OCR text extraction for scan pages (V3)
- PaddleOCR OneDnnContext compatibility issues (V5 - isolated PaddleOCR)

### Security
- No secrets or PII in logs
- Configuration via environment variables

## [Unreleased]

### Planned
- Advanced QA checkers (SemanticSectionChecker, TableCellChecker, BalanceSheetChecker, CrossRefChecker, DiffChecker)
- GPU worker queue for VRAM management
- Visual tables path (PP-StructureV3)
- Performance optimizations
