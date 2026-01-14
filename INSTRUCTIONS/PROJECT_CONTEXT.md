# PROJECT CONTEXT

## 1) Project Summary
**Product / repo name:** PDF Type Router
**One-line goal:** Pipeline that classifies each PDF page (and regions) as digital/scanned/mixed and routes to appropriate extraction path
**Primary users:** Developers working with financial document parsing (financial statements)
**Core use-cases:**
- Page-level classification (digital vs scanned vs mixed)
- Digital-first path: native text extraction + vector tables (Camelot/Tabula) + minimal OCR only for missing regions
- Scan-first path: rendering + layout/regions + OCR (region-wise) + table cell structure + validation
- Merge & reading order reconstruction
- Normalization & QA (sum/trial balance/cross-reference checks) and export (JSON+MD)
**Non-goals:**
- Assuming entire PDF is one type (classification is page-wise)
- Running OCR unnecessarily (only when needed)
- Treating tables as plain text (tables handled as separate channel)

## 2) Current State
**Repo path:** `F:\-DEV-\36.PDF-tyyppireititin`
**What works today:**
- Full pipeline implementation (Steps 00-70)
- Tesseract OCR as primary OCR engine (V5)
- Fallback logic for OCR
- Basic QA checkers
**What's broken / missing:**
- Advanced QA checkers (SemanticSectionChecker, TableCellChecker, BalanceSheetChecker, CrossRefChecker, DiffChecker)
- GPU worker queue for VRAM management
- Visual tables path (PP-StructureV3)
**Constraints:**
- GPU acceleration should be used when beneficial (PP-StructureV3, OCR, MinerU/VLM parsing, heavy image processing)
- Native PDF text extraction and vector tables often fast enough on CPU
- Must handle large documents (100+ pages) efficiently
- Windows environment (Poppler, Tesseract paths)

## 3) Tech Stack
**Core:**
- Python 3.10+
- PyMuPDF (fitz) - PDF parsing
- pdfplumber - Text extraction
- pdf2image + Poppler - PDF rendering
- OpenCV (cv2) - Image processing, layout detection
- PaddleOCR (PP-StructureV3) - OCR tables (optional, isolated)
- Tesseract OCR - Primary OCR engine (V5)
- Pydantic - Data validation
- orjson - Fast JSON

**Optional:**
- Camelot/Tabula - Vector table extraction
- MinerU - Advanced document parsing
- PyTorch - GPU acceleration
- PaddlePaddle - PaddleOCR backend

## 4) Repository Boundaries
**In scope:**
- PDF page classification
- Text extraction (native + OCR)
- Table extraction (vector + OCR)
- Layout region detection
- Reading order reconstruction
- Semantic classification
- QA checks
- Export (JSON + Markdown)

**Out of scope:**
- PDF generation
- Web UI
- Database storage
- API server

## 5) Definition of Done
**V5 DoD:**
- ✅ Tesseract OCR installed and working
- ✅ Pipeline produces non-empty `document.json`
- ✅ `blocks_ocr/` contains data
- ✅ Fallback logic works
- ⏳ Advanced QA checkers (pending)

## 6) Decision Log
- **V5:** Tesseract OCR as primary engine (PaddleOCR isolated due to OneDnnContext issues)
- **V4:** Attempted PaddleOCR stabilization (failed)
- **V3:** Added OCR text extraction for scan pages
- **V2:** Fixed empty document.json issue
- **V1:** Initial pipeline implementation
