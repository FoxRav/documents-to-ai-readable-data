# Cursor-ohje | PDF-tyyppireititin — Canvas v4

## Tarkoitus (v4)
V4 keskittyy yhteen asiaan: **OCR:n stabilointi** siten, että scan/mixed-sivuista syntyy aina tekstiä (`blocks_ocr/` ja `document.json`).

Lähtötilanne v3-ajosta:
- `blocks_ocr/`: 0/154 tiedostoa sisältää dataa
- `document.json`: tyhjä (0 items)
- PaddleOCR: OneDnnContext-virhe (GPU/CPU)
- PaddleOCR palauttaa tyhjän tuloksen (ei poikkeusta) → fallback ei aiemmin käynnistynyt
- pytesseract-fallback ei toiminut (binääri/path)

---

# 0) V4-periaate

> Jos ensisijainen OCR palauttaa 0 blokkia, se on virhe — fallback on pakko käynnistää.

V4 koostuu 3 gatea:
1) **PaddleOCR eloon** (GPU tai CPU)
2) **pytesseract eloon** (oikea asennus + PATH)
3) **Fallback-logiikka** (empty-result → fallback)

---

# 1) Gate A — Tee PaddleOCR toimivaksi (ensin CPU, sitten GPU)

## 1.1 Pikatesti (erillinen skripti)
Luo `tools/ocr_smoke_test.py`:
- lataa 1 renderöity sivu PNG
- aja PaddleOCR (text) ja tulosta blokkimäärä

Tavoite:
- `blocks_count > 0` yhdellä selkeällä sivulla

## 1.2 Aja ensin CPU-mode
Miksi: OneDnnContext/MKLDNN/oneDNN-ongelmat voivat rikkoa inferenssin.

Toimi:
- lisää konfiin `OCR_DEVICE=cpu`
- disabloi CPU-kiihdytykset jotka aiheuttavat ongelmia:
  - `use_mkldnn = False` (jos käytössä)
  - pidä asetukset minimissä (ei orientation/unwarping)

Jos CPU toimii (blokkeja syntyy):
- siirry kohtaan 1.3

## 1.3 GPU-mode vasta kun CPU toimii
- lisää konfiin `OCR_DEVICE=cuda`
- varmista Paddle/PaddleOCR -versioyhteensopivuus CUDA:n kanssa
- käytä `GPU_CONCURRENCY=1`

Jos GPU palauttaa 0 blokkia tai kaatuu:
- pidä pipeline CPU-OCR:llä toistaiseksi
- jatka v4:ssä eteenpäin (fallback vaaditaan silti)

---

# 2) Gate B — Tee pytesseract oikeasti toimivaksi

## 2.1 Vaatimukset
pytesseract Python-paketti EI riitä. Tarvitset:
- Windows Tesseract-OCR asennettuna
- `tesseract.exe` PATH:ssa tai asetettuna eksplisiittisesti koodissa

## 2.2 Pikatesti
PowerShell:
- `tesseract --version` pitää toimia

Python:
- testaa 1 kuva → `image_to_string` tuottaa tekstiä

## 2.3 Koodimuutos (turvallinen)
Lisää konfiin:
- `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` (esimerkki)

Ja koodissa:
- `pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD`

---

# 3) Gate C — Fallback-logiikka (tyhjä tulos = fallback)

## 3.1 Pakollinen ehto
Jos PaddleOCR palauttaa:
- `None`, `[]`, tai `blocks_count == 0`

→ käynnistä **pytesseract** samalla inputilla.

## 3.2 Fallback-resultin normalisointi
Kaikki OCR-lähteet normalisoidaan samaan muotoon:
- `block_id`
- `text`
- `bbox`
- `confidence` (jos tesseract: arvioi heuristiikalla tai aseta `null`)
- `source`: `paddleocr|tesseract`

## 3.3 Logitus (pakollinen)
Kirjaa aina per-sivu:
- `paddle_blocks`
- `tesseract_blocks`
- `ocr_source_used`

---

# 4) V4-ajostrategia (minimoi riskit)

## 4.1 Aja ensin 3–5 sivun mini-run
- valitse sivut: 1, 2, 3, ja 1 taulukko-sivu, 1 liite-sivu
- aja pipeline vain näille

DoD mini-run:
- `blocks_ocr/` ei ole tyhjä
- `document.json` ei ole tyhjä

## 4.2 Aja sitten koko dokumentti
Kun mini-run ok:
- aja kaikki 154 sivua
- pidä `GPU_CONCURRENCY=1`

---

# 5) V4 Definition of Done

V4 on valmis, kun:
- PaddleOCR toimii vähintään CPU:lla (smoke test läpi)
- pytesseract toimii (tesseract --version ok + python test ok)
- pipeline tuottaa `blocks_ocr/`-dataa (ei 0/154)
- `document.json` ei ole tyhjä
- fallback käynnistyy automaattisesti, jos PaddleOCR palauttaa 0 blokkia

---

# 6) V4 → V5 siirtymäsääntö

Vasta kun V4 DoD täyttyy:
- jatka QA-checkereihin
- lisää visual tables -polku
- lisää GPU-worker queue (jos ei vielä)

---

**Muistisääntö:**
> OCR ensin eloon deterministisesti (CPU → GPU), ja fallback pakolliseksi.

