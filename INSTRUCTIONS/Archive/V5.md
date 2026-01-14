# Cursor-ohje | PDF-tyyppireititin — Canvas v5

## Tarkoitus (v5)
V5 tekee OCR:stä **tuotantokelpoisen nyt** riippumatta PaddleOCR:n rikkoutumisesta.

Tilanne v4 jälkeen:
- PaddleOCR ei toimi (OneDnnContext myös CPU:lla) → **ei luotettava**
- Fallback-logiikka on toteutettu (tyhjä tulos → fallback)
- pytesseract Python-paketti asennettu, mutta **Tesseract binääri puuttuu**

V5 ratkaisee tämän kolmella päätöksellä:
1) **Tesseract on pakollinen riippuvuus Windowsissa**
2) Pipeline käyttää Tesseractia ensisijaisena OCR:na kun PaddleOCR on epäluotettava
3) PaddleOCR pidetään eristettynä optioksi (ei blokkaa ajoa)

---

# 0) V5-periaate

> OCR ei saa olla "best effort". Jokaiselta scan/mixed-sivulta on synnyttävä tekstiä tai pipeline failaa selkeällä syyllä.

---

# 1) Gate B2 — Asenna Tesseract Windowsiin (pakollinen)

## 1.1 Asennus
Asenna Tesseract (Windows):
- Lähde: UB Mannheim build
- Oletuspolku:
  - `C:\Program Files\Tesseract-OCR\tesseract.exe`

## 1.2 Verifiointi
PowerShell:
- `tesseract --version` (pakollinen)

Jos komento ei löydy:
- lisää asennushakemisto PATH:iin
- tai käytä `TESSERACT_CMD` asetusta

## 1.3 .env (pakollinen)
Lisää `.env`:
- `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

Lisää myös:
- `OCR_PRIMARY=tesseract`
- `OCR_FALLBACK=none` (väliaikaisesti)

---

# 2) Gate C2 — OCR-strategia (PaddleOCR pois polulta)

## 2.1 Valitsimet (v5)
Lisää asetukset:
- `OCR_PRIMARY=tesseract|paddle`
- `OCR_FALLBACK=tesseract|paddle|none`

V5 oletus:
- `OCR_PRIMARY=tesseract`
- `OCR_FALLBACK=none`

## 2.2 Käyttölogiikka
- Jos `OCR_PRIMARY=tesseract`: aja aina tesseract scan/mixed-sivuille
- Jos myöhemmin halutaan Paddle takaisin:
  - `OCR_PRIMARY=paddle`
  - fallback on pakollinen: `OCR_FALLBACK=tesseract`
  - ja tyhjä tulos tulkitaan virheeksi

---

# 3) Gate C3 — Fallback edelleen pakollinen (tyhjä tulos)

Vaikka v5:ssä ajetaan Tesseract ensisijaisena, pidä sama sääntö:
- jos OCR palauttaa 0 blokkia →
  - merkitse sivu epäonnistuneeksi
  - kirjaa syy
  - (jos fallback sallittu) aja fallback

---

# 4) Gate D — Mini-run ennen koko dokumenttia

## 4.1 Valitse testisivut
- 3–5 sivua:
  - 1 kansi/tekstisivu
  - 1 liitesivu
  - 1 taulukko-sivu
  - 1 mahdollinen skannattu sivu

## 4.2 DoD mini-run
- `blocks_ocr/` sisältää dataa
- `document.json` ei ole tyhjä
- OCR-lähde raportoitu (tesseract)

---

# 5) V5 Definition of Done

V5 on valmis, kun:
- Tesseract on asennettu ja `tesseract --version` toimii
- `.env` sisältää `TESSERACT_CMD`
- Mini-run tuottaa ei-tyhjän `document.json`
- Koko dokumentin ajo tuottaa `blocks_ocr/` dataa

---

# 6) V5 → V6

Kun v5 toimii:
- palauta PaddleOCR tutkittavaksi erillisessä branchissa / envissä
- harkitse vaihtoehtoisia open-source OCR:ia (esim. OCRmyPDF + Tesseract, EasyOCR)
- jatka QA-checkereihin vasta kun V5 on stabiili

---

**Muistisääntö:**
> Tee ensin toimiva perus-OCR (Tesseract). Palauta nopeammat/paremmat moottorit vasta kun perusta on stabiili.

