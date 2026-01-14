# Cursor-ohje | PDF-tyyppireititin — Canvas v2

## Tarkoitus (v2)
Tämä canvas kuvaa **todellisen v1-ajon jälkeisen tilanteen**, tunnistetut viat ja **pakollisen korjauskierroksen**. V2 ei lisää uusia ominaisuuksia, vaan varmistaa että **data virtaa oikein** ennen jatkokehitystä.

---

# 0) Lähtötilanne (v1-ajo)

Pipeline on ajettu kokonaan (Step 00–70), mutta tulos ei ollut hyväksyttävä.

### Havaittu oire
- `document.json` syntyy, mutta:
  - `pages[].items == []` kaikilla sivuilla

### Juuri­s yy (todettu)
- Kaikki sivut luokiteltiin `scan`
- Step 10 (natiivi tekstipoiminta) ei ajanut
- Step 41 käsitteli vain taulukoita
- **Tekstialueiden OCR puuttui (41B puuttui)**

Seurauksena: pipeline ajoi teknisesti loppuun, mutta **tuotti nolladataa**.

---

# 1) V2-periaate (kriittinen)

> Pipeline ei ole onnistunut, jos `document.json` on tyhjä — vaikka ajo ei kaatuisi.

V2 keskittyy vain yhteen asiaan:
**scan/mixed-sivuilta on pakko tulla sisältöä.**

---

# 2) Pakolliset korjaukset v2:ssa

## 2.1 Step 41 vastuu (scan/mixed)

Step 41 **on viimeinen puolustuslinja**.

Pakollista:
- 41A: taulukot (jos löytyy)
- **41B: OCR-tekstialueet (aina)**

Jos taulukoita ei löydy:
- tekstiblokit riittävät
- dokumentti ei saa jäädä tyhjäksi

Jokaisesta OCR-tekstiblokista:
- `block_id`
- `text`
- `bbox`
- `confidence`

---

## 2.2 Sivutyyppiluokittelu (guardrail)

Lisää v2:ssa tarkistus:
- Jos **kaikki sivut** luokittuvat `scan`:
  - liputa varoitus
  - pakota Step 41B kaikille sivuille

---

# 3) V2-tarkistuskierros (ajon jälkeen)

Aja aina tämä järjestyksessä:

1) Pipeline ajoi kaikki stepit
2) `document.json` ei ole tyhjä
3) Scan-sivuilta löytyy tekstiblokkeja
4) `blocks_ocr/` ei ole tyhjä
5) Vasta nyt jatka QA:han

Jos kohta 2 epäonnistuu → **palaa Step 41:een**.

---

# 4) Toteutettu v1 + v2 tähän asti

- [x] Pipeline-rakenne (00–70)
- [x] OCR GPU-tuella
- [x] Rinnakkaistettu alueiden tunnistus
- [x] **OCR-tekstialueet lisätty Step 41B:hen**

---

# 5) Puuttuvat osat (EI tehdä ennen kuin data kulkee)

Näitä **ei saa toteuttaa ennen kuin v2 DoD täyttyy**:

- QA-checkerit:
  - SemanticSectionChecker
  - TableCellChecker
  - BalanceSheetChecker
  - CrossRefChecker
  - DiffChecker
- GPU-worker queue
- Visual tables -polku (PP-StructureV3)

---

# 6) V2 Definition of Done

V2 on valmis, kun:

- `document.json` sisältää dataa jokaiselta sivulta
- Scan-sivut tuottavat vähintään tekstiblokit
- Pipeline voidaan ajaa uudelleen ilman käsin tehtyjä hotfixejä
- Yksikään sivu ei jää `items: []` tilaan

---

# 7) V2 → V3 siirtymäsääntö

Vasta kun V2 DoD täyttyy:
- aloita QA-checkerien toteutus
- lisää GPU-worker queue
- ota visual tables käyttöön

---

**Muistisääntö:**
> Ensin data. Vasta sitten älykkyys.

