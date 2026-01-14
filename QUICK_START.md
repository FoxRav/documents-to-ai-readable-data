# Quick Start Guide

## 1. Check Environment

```powershell
# Python
python --version

# Dependencies
pip install -e .

# Tesseract (REQUIRED)
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

## 2. Verify Tesseract OCR

**✅ Tesseract OCR is already installed!** (v5.4.0.20240606)

Test:
```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

## 3. Check .env

The `.env` file is already created. Verify the path is correct:
```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## 4. Run Pipeline

```powershell
# Place PDF in data/00_input/ directory

# Prepare assets (first time only)
python -m src.pipeline.run_all --pdf data/00_input/your_file.pdf --prepare-assets

# Run pipeline
python -m src.pipeline.run_all --pdf data/00_input/your_file.pdf
```

## 5. Verify Results

```powershell
# Check OCR blocks
Get-ChildItem "data\10_work\blocks_ocr\*.jsonl" | Where-Object { (Get-Content $_.FullName -Raw).Length -gt 0 } | Measure-Object

# Check document.json
python -c "import json; d=json.load(open('out/document.json')); print(f'Pages: {len(d[\"pages\"])}, Total items: {sum(len(p.get(\"items\", [])) for p in d[\"pages\"])}')"
```

## Issues?

See `RESTART_GUIDE.md` for detailed instructions.
