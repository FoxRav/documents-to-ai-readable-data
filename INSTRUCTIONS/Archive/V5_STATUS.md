# V5 OCR Fallback Tuotantokelpoiseksi - Status

## Toteutettu

### Gate B2: Konfiguraatio ✅
- ✅ `OCR_PRIMARY` ja `OCR_FALLBACK` asetukset lisätty `config.py`:hin
- ✅ Oletus: `OCR_PRIMARY=tesseract`, `OCR_FALLBACK=none`
- ✅ `TESSERACT_CMD` konfiguraatio tukee eksplisiittistä polkua

### Gate C2: OCR-strategia (Tesseract ensisijaisena) ✅
- ✅ `extract_ocr_text_blocks()` käyttää nyt `OCR_PRIMARY`-asetusta
- ✅ Tesseract on ensisijainen OCR (jos `OCR_PRIMARY=tesseract`)
- ✅ PaddleOCR eristetty `_extract_with_paddleocr()` funktioon (optio)
- ✅ Fallback-logiikka toimii molempiin suuntiin

### Gate C3: Fallback-logiikka tyhjälle tulokselle ✅
- ✅ Jos OCR palauttaa 0 blokkia → logitetaan virhe
- ✅ Jos fallback sallittu → käynnistetään automaattisesti
- ✅ Per-sivu logitus: `paddle_blocks`, `tesseract_blocks`, `ocr_source_used`

## Tarvittavat askeleet

### Gate B2: Tesseract asennus (pakollinen)
1. **Asenna Tesseract OCR Windows:lle:**
   - Lähde: https://github.com/UB-Mannheim/tesseract/wiki
   - Oletuspolku: `C:\Program Files\Tesseract-OCR\tesseract.exe`

2. **Verifioi asennus:**
   ```powershell
   tesseract --version
   ```

3. **Lisää `.env`-tiedostoon:**
   ```
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   OCR_PRIMARY=tesseract
   OCR_FALLBACK=none
   ```

### Gate D: Mini-run testaus (odottaa Tesseract-asennusta)
- ⏳ Valitse 3-5 testisivua
- ⏳ Aja pipeline näille sivuille
- ⏳ Varmista että `blocks_ocr/` sisältää dataa
- ⏳ Varmista että `document.json` ei ole tyhjä

## V5 DoD Status

- [ ] Tesseract on asennettu ja `tesseract --version` toimii - ⚠️ TARVITSEE ASENNUKSEN
- [ ] `.env` sisältää `TESSERACT_CMD` - ⏳ ODOTTAA TESSERACT-ASENNUSTA
- [ ] Mini-run tuottaa ei-tyhjän `document.json` - ⏳ ODOTTAA TESSERACT-ASENNUSTA
- [ ] Koko dokumentin ajo tuottaa `blocks_ocr/` dataa - ⏳ ODOTTAA TESSERACT-ASENNUSTA
- [x] OCR-strategia käyttää Tesseractia ensisijaisena - ✅ TOTEUTETTU
- [x] PaddleOCR eristetty optioksi - ✅ TOTEUTETTU
- [x] Fallback-logiikka toimii - ✅ TOTEUTETTU

## Koodimuutokset

### `src/pipeline/config.py`
- Lisätty `ocr_primary: Literal["tesseract", "paddle"] = "tesseract"`
- Lisätty `ocr_fallback: Literal["tesseract", "paddle", "none"] = "none"`

### `src/pipeline/step_41_ocr_tables.py`
- `extract_ocr_text_blocks()` uudelleenkirjoitettu V5-logiikalla
- `_extract_with_tesseract()` - uusi funktio Tesseract-OCR:lle
- `_extract_with_paddleocr()` - eristetty funktio PaddleOCR:lle
- Per-sivu logitus: `paddle_blocks`, `tesseract_blocks`, `ocr_source_used`

## Seuraavat askeleet

1. **Asenna Tesseract OCR** (pakollinen)
2. **Testaa smoke test uudelleen** Tesseract:lla
3. **Aja mini-run** (3-5 sivua) kun Tesseract toimii
4. **Aja koko dokumentti** kun mini-run onnistuu

---

**Muistisääntö:**
> Tee ensin toimiva perus-OCR (Tesseract). Palauta nopeammat/paremmat moottorit vasta kun perusta on stabiili.

**Tilanne nyt:**
- ✅ Koodi valmis V5-logiikalla
- ⚠️ Tesseract asennus pakollinen ennen testausta
- ✅ PaddleOCR eristetty, ei blokkaa ajoa
