# Project Restart Guide

## 1) Environment Check

### Python Environment
```powershell
# Check Python version
python --version

# Check if virtual environment is activated (if in use)
# If not, activate it:
# .venv\Scripts\Activate.ps1
```

### Dependencies
```powershell
# Install dependencies (if missing)
pip install -e .
```

### Key Dependencies
- `pymupdf` (PyMuPDF)
- `pdfplumber`
- `pdf2image`
- `opencv-python`
- `pytesseract`
- `paddleocr` (optional, not required in V5)

---

## 2) Tesseract OCR Installation (REQUIRED)

**The `.env` file is already created in the project root!**

### Windows Installation
1. **Read first:** `INSTALL_TESSERACT.md` (detailed instructions)
2. Download Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
3. Install (default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`)
4. Verify:
   ```powershell
   & "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
   ```

### Configuration
The `.env` file is already created. Verify the path is correct:
```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_PRIMARY=tesseract
OCR_FALLBACK=none
```

If you installed to a different path, update the `.env` file.

---

## 3) Project Directory Structure

Ensure the following directories exist:
```
data/
  ├── 00_input/          # PDF files go here
  ├── 10_work/           # Temporary files
  │   ├── page_manifest/
  │   ├── pages_png/
  │   ├── regions/
  │   ├── blocks_ocr/
  │   └── debug/
  └── ...
out/                     # Final results
  ├── document.json
  ├── document.md
  └── qa_report.json
```

---

## 4) Pipeline Execution

### Basic Execution
```powershell
python -m src.pipeline.run_all --pdf data/00_input/your_file.pdf
```

### Options
```powershell
# Asset check before execution
python -m src.pipeline.run_all --pdf data/00_input/your_file.pdf --prepare-assets

# Debug logging
python -m src.pipeline.run_all --pdf data/00_input/your_file.pdf --log-level DEBUG

# JSON logging
python -m src.pipeline.run_all --pdf data/00_input/your_file.pdf --log-format json
```

### Mini-run Testing (3-5 pages)
Before running the full document, test with a few pages:
```powershell
# Modify run_all.py temporarily to limit page count
# Or use a PDF with only a few pages
```

---

## 5) Post-Run Checks

### V5 Checks
```powershell
# 1. Check blocks_ocr/
Get-ChildItem "data\10_work\blocks_ocr\*.jsonl" | Where-Object { (Get-Content $_.FullName -Raw).Length -gt 0 } | Measure-Object

# 2. Check document.json
python -c "import json; d=json.load(open('out/document.json')); print(f'Pages: {len(d[\"pages\"])}, Total items: {sum(len(p.get(\"items\", [])) for p in d[\"pages\"])}')"

# 3. Check for empty pages
python -c "import json; d=json.load(open('out/document.json')); empty=sum(1 for p in d['pages'] if len(p.get('items', []))==0); print(f'Empty pages: {empty}/{len(d[\"pages\"])}')"
```

### OCR Source Check
```powershell
# Check logs for which OCR was used
Select-String -Path "*.log" -Pattern "OCR summary|Tesseract extracted|PaddleOCR extracted"
```

---

## 6) Troubleshooting

### Tesseract Not Found
```
Error: tesseract is not installed or it's not in your PATH
```
**Solution:**
1. Install Tesseract OCR
2. Add to `.env` file: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

### OCR Returns 0 Blocks
```
WARNING: OCR text extraction returned 0 blocks for page X
```
**Check:**
1. Is Tesseract installed and configured?
2. Do rendered PNG images exist in `data/10_work/pages_png/`?
3. Check logs for OCR errors

### document.json is Empty
```
ERROR: Document is empty - Step 41B failed to extract data
```
**Solution:**
1. Check that `blocks_ocr/` contains data
2. Check OCR logs
3. Verify Tesseract works: `& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version`

---

## 7) Quick Checklist

- [ ] Python installed and working
- [ ] Dependencies installed (`pip install -e .`)
- [ ] Tesseract OCR installed and `tesseract --version` works
- [ ] `.env` file created and `TESSERACT_CMD` set
- [ ] Test PDF in `data/00_input/` directory
- [ ] Pipeline execution succeeds
- [ ] `blocks_ocr/` contains data
- [ ] `document.json` is not empty

---

## 8) Next Steps

When V5 DoD is met:
1. Continue to QA checkers
2. Add visual tables path
3. Consider fixing PaddleOCR in a separate branch

---

**Last update:** V5 (Tesseract as primary OCR)
