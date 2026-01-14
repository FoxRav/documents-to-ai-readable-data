# Tesseract OCR Installation Guide (Windows)

## Required Installation

Tesseract OCR is a **required** dependency in V5. It is the primary OCR engine.

## Installation

### Automatic Installation (Recommended)

**Windows Package Manager (winget):**
```powershell
winget install --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
```

This automatically installs Tesseract OCR to the default path: `C:\Program Files\Tesseract-OCR\`

### Manual Installation

**1. Download Tesseract OCR**

**Source:** https://github.com/UB-Mannheim/tesseract/wiki

**Recommended version:** Tesseract 5.x (latest stable version)

**Download links:**
- 64-bit: https://github.com/UB-Mannheim/tesseract/releases
- Select the latest `tesseract-ocr-w64-setup-*.exe` file

**2. Install Tesseract**

1. Run the downloaded installer (`tesseract-ocr-w64-setup-*.exe`)
2. **Important:** Install to default path: `C:\Program Files\Tesseract-OCR\`
3. During installation:
   - ✅ Select "Add to PATH" (if available)
   - ✅ Install Finnish language package (fin)

### 3. Verify Installation

Open PowerShell and test:

```powershell
# Check version (with explicit path, if not in PATH)
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

# Should show something like:
# tesseract v5.4.0.20240606
#  leptonica-1.84.1
#   libgif 5.2.1 : libjpeg 8d (libjpeg-turbo 3.0.1) : libpng 1.6.43 : libtiff 4.6.0
```

**Note:** Tesseract may not be in PATH, but the `.env` file uses an explicit path.

### 4. Test from Python

```powershell
cd "f:\-DEV-\36.PDF-tyyppireititin"
python -c "import pytesseract; pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'; print('Tesseract version:', pytesseract.get_tesseract_version())"
```

**Note:** The `.env` file configures the path automatically, so the pipeline will use the correct path.

### 5. Configure .env

The `.env` file is already created in the project root. Verify the path is correct:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

If you installed to a different path, update the `.env` file.

## Troubleshooting

### "tesseract is not recognized"

**Solution:**
1. Check that Tesseract is installed: `Get-ChildItem "C:\Program Files\Tesseract-OCR\tesseract.exe"`
2. If found, add to `.env` file: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`
3. If not found, reinstall Tesseract

### "Tesseract not found in PATH"

**Solution:**
- Use the `.env` file with explicit path
- Verify the path is correct: `Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe"`

### Finnish Language Missing

**Solution:**
1. Reinstall Tesseract
2. Select Finnish language package during installation
3. Or download separately: https://github.com/tesseract-ocr/tessdata

## Testing in Pipeline

When Tesseract is installed, test:

```powershell
# Smoke test
python tools/ocr_smoke_test.py "data/10_work/pages_png/page_0000.png"

# Should show:
# Tesseract: X blocks found
```

## Next Steps

When Tesseract is installed and tested:
1. ✅ `.env` file configured
2. ✅ `tesseract --version` works
3. ✅ Python test works
4. → Run pipeline: `python -m src.pipeline.run_all --pdf "data/00_input/your-file.pdf"`
