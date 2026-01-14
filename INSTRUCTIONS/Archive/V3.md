# Cursor-ohje | PDF-tyyppireititin — Canvas v3

## Tarkoitus (v3)
Canvas v3 ohjaa **korjatun pipelinen täyden uudelleenajon** ja sen jälkeisen verifioinnin. Tässä vaiheessa oletetaan, että v2-korjaukset (erityisesti Step 41B OCR-tekstialueet) ovat käytössä.

Tavoite: todistaa, että **data virtaa päästä päähän** ja että pipeline tuottaa ei-tyhjän, analysoitavan `document.json`-tuloksen.

---

# 0) Lähtötilanne

Pipeline käynnistetty taustalla:
- Stepit: 00–70
- Sivut: 154
- OCR: CUDA käytössä
- Kieliasetus: `en`
- Debug-logitus: päällä

Odotusaika:
- 10–30 min (GPU-riippuvainen)

---

# 1) Pakolliset tarkistukset ajon aikana

## 1.1 Elonmerkit (runtime)
Tarkista ajon aikana:
- GPU-käyttö nousee OCR-vaiheessa
- Logeissa näkyy `Step 41B`-ajo
- `blocks_ocr/`-hakemistoon syntyy uusia `.jsonl`-tiedostoja

Jos `blocks_ocr/` pysyy tyhjänä yli 10 min:
- keskeytä ajo
- tarkista OCR-kieliasetus ja CUDA-initialisointi

---

# 2) Pakolliset tarkistukset ajon jälkeen (v3-gate)

Suorita **tässä järjestyksessä**:

## 2.1 OCR-tuotokset
- [ ] `blocks_ocr/` sisältää tiedostoja
- [ ] Yhdessä `.jsonl`-tiedostossa on useita tekstiblokkeja
- [ ] Blokeissa on `text`, `bbox`, `confidence`

## 2.2 Dokumenttirakenne
- [ ] `document.json` on olemassa
- [ ] `pages[].items.length > 0` kaikilla tai lähes kaikilla sivuilla
- [ ] Ei massiivista `items: []` -ilmiötä

## 2.3 Sivutyyppijakauma
- [ ] Kaikki sivut eivät ole `scan`
- [ ] Jos ovat, OCR-tekstiblokit silti olemassa

---

# 3) Tyypilliset v3-virhetilanteet

## 3.1 OCR tuottaa dataa, mutta merge epäonnistuu
Oire:
- `blocks_ocr/` OK
- `document.json` lähes tyhjä

Toimi:
- tarkista Step 50 (merge)
- varmista, että OCR-blokit lisätään `items[]`

## 3.2 OCR-teksti on roskaa
Oire:
- tekstiä on, mutta se on käyttökelvotonta

Toimi:
- tarkista kieliasetus
- tarkista DPI / renderöinti
- tarkista logeista varoitukset

---

# 4) V3 Definition of Done

V3 katsotaan onnistuneeksi, kun:

- `blocks_ocr/` sisältää OCR-dataa kaikilta scan/mixed-sivuilta
- `document.json` sisältää sisältöä (teksti ja/tai taulukot)
- Data on rakenteellisesti hyödynnettävissä (ei pelkkää kohinaa)
- Pipeline voidaan ajaa uudelleen samoilla asetuksilla

---

# 5) V3 → V4 siirtymäsääntö

Vasta kun V3 DoD täyttyy:
- aloita QA-checkerien toteutus
- lisää GPU-worker queue
- ota visual tables -polku käyttöön

---

**Muistisääntö:**
> Jos data liikkuu, kaikki muu on ratkaistavissa.

