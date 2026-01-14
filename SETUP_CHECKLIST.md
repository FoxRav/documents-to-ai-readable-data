# Project Setup and Verification Checklist

## Before First Run

### ✅ Python Environment
- [ ] Python 3.10+ installed
- [ ] Dependencies installed: `pip install -e .`
- [ ] Python packages working (pymupdf, pdfplumber, pdf2image, opencv, pytesseract)

### ✅ Tesseract OCR (INSTALLED)
- [x] Tesseract OCR installed on Windows ✅
- [x] Installation path: `C:\Program Files\Tesseract-OCR\tesseract.exe` ✅
- [x] Version: 5.4.0.20240606 ✅
- [x] Python test: Works with explicit path ✅
- [x] `.env` file configured ✅

### ✅ Configuration
- [x] `.env` file created in project root
- [x] `TESSERACT_CMD` set to correct path
- [x] `OCR_PRIMARY=tesseract` set
- [ ] Other settings verified

### ✅ Project Directory Structure
- [ ] `data/00_input/` - directory for PDF files
- [ ] `data/10_work/` - directory for temporary files
- [ ] `out/` - directory for final results

### ✅ Test PDF
- [ ] Test PDF file in `data/00_input/` directory

## First Run

### 1. Smoke Test (optional)
```powershell
# If rendered images already exist
python tools/ocr_smoke_test.py "data/10_work/pages_png/page_0000.png"
```

### 2. Pipeline Execution
```powershell
python -m src.pipeline.run_all --pdf "data/00_input/your-file.pdf"
```

### 3. Post-Run Checks
```powershell
# Check blocks_ocr/
Get-ChildItem "data\10_work\blocks_ocr\*.jsonl" | Where-Object { (Get-Content $_.FullName -Raw).Length -gt 0 } | Measure-Object

# Check document.json
python -c "import json; d=json.load(open('out/document.json')); print(f'Pages: {len(d[\"pages\"])}, Total items: {sum(len(p.get(\"items\", [])) for p in d[\"pages\"])}')"
```

## Troubleshooting

### Tesseract Not Found
- Check installation: `Get-ChildItem "C:\Program Files\Tesseract-OCR\tesseract.exe"`
- Check `.env`: `TESSERACT_CMD` path
- See: `INSTALL_TESSERACT.md`

### OCR Returns 0 Blocks
- Check Tesseract installation
- Check logs for OCR errors
- Verify rendered PNG images exist

### document.json Empty
- Check that `blocks_ocr/` contains data
- Check OCR logs
- Verify Tesseract works

## Quick Check

```powershell
# 1. Python
python --version

# 2. Dependencies
python -c "import pymupdf, pdfplumber, pdf2image, cv2, pytesseract; print('All packages OK')"

# 3. Tesseract
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

# 4. .env
Test-Path ".env"

# 5. Test PDF
Test-Path "data\00_input\*.pdf"
```

## Next Steps

When all checks are OK:
1. Run pipeline with test PDF
2. Verify results
3. If OK, run full document

---

**Last update:** V5 (Tesseract as primary)
