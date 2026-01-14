# V4 OCR Stabilointi - Status

## Gate A: PaddleOCR (CPU ensin) - ❌ EPÄONNISTUI

**Ongelma:**
- OneDnnContext-virhe myös CPU:lla MKLDNN:n disabloinnilla
- PaddleOCR-versio/yhteensopivuusongelma

**Kokeillut korjaukset:**
- ✅ MKLDNN disabloitu (`use_mkldnn=False`, `FLAGS_use_mkldnn=0`)
- ✅ CPU-mode ensin
- ❌ Ei toimi - sama OneDnnContext-virhe

**Seuraava askel:**
- PaddleOCR-versio päivitys tai vaihtoehtoinen OCR-ratkaisu
- **Kriittinen:** Fallback-logiikka (Gate C) on nyt pakollinen

---

## Gate B: pytesseract - ⚠️ TARVITSEE ASENNUKSEN

**Tilanne:**
- pytesseract Python-paketti: ✅ Asennettu
- Tesseract OCR binääri: ❌ Ei asennettuna

**Tarvittava asennus:**
1. Lataa Tesseract OCR Windows:lle: https://github.com/UB-Mannheim/tesseract/wiki
2. Asenna (oletuspolku: `C:\Program Files\Tesseract-OCR\tesseract.exe`)
3. Lisää `.env`-tiedostoon:
   ```
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

**Testaus:**
```powershell
tesseract --version
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

---

## Gate C: Fallback-logiikka - ✅ TOTEUTETTU

**Toteutus:**
- ✅ PaddleOCR palauttaa 0 blokkia → pytesseract-fallback käynnistyy
- ✅ Konfiguraatio tukee TESSERACT_CMD -asetusta
- ✅ Logitus: `paddle_blocks`, `tesseract_blocks`, `ocr_source_used`

**Koodi:**
- `src/pipeline/step_41_ocr_tables.py`: Fallback-logiikka toimii
- `src/pipeline/config.py`: OCR-asetukset lisätty

---

## V4 DoD Status

- [ ] PaddleOCR toimii vähintään CPU:lla (smoke test läpi) - ❌ EPÄONNISTUI
- [ ] pytesseract toimii (tesseract --version ok + python test ok) - ⚠️ TARVITSEE ASENNUKSEN
- [ ] pipeline tuottaa `blocks_ocr/`-dataa (ei 0/154) - ⏳ ODOTTAA TESSERACT-ASENNUSTA
- [ ] `document.json` ei ole tyhjä - ⏳ ODOTTAA TESSERACT-ASENNUSTA
- [x] fallback käynnistyy automaattisesti, jos PaddleOCR palauttaa 0 blokkia - ✅ TOTEUTETTU

---

## Seuraavat askeleet

1. **Asenna Tesseract OCR** (Gate B)
2. **Testaa smoke test uudelleen** pytesseract:lla
3. **Aja mini-run** (3-5 sivua) kun Tesseract toimii
4. **Jos PaddleOCR ei toimi:** jatka pelkällä pytesseract:lla

---

**Muistisääntö:**
> OCR ensin eloon deterministisesti (CPU → GPU), ja fallback pakolliseksi.

**Tilanne nyt:**
- PaddleOCR ei toimi → fallback on **kriittinen**
- Tesseract asennus → **pakollinen seuraava askel**
