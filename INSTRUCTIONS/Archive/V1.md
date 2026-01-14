# v1 | PDF-tyyppireititin + koko stäkki (digitaalinen vs skannattu)

## Johtopäätös
Rakennetaan pipeline, joka **luokittelee jokaisen PDF-sivun (ja tarvittaessa alueet) digitaaliseksi / skannatuksi / sekoitetuksi** ja valitsee sen mukaan oikean poimintareitin:
- **Digital-first**: natiivi tekstipoiminta + vektoritaulukot (Camelot/Tabula) + minimaalinen OCR vain puuttuviin alueisiin.
- **Scan-first**: renderöinti + layout/alueet + OCR (aluekohtaisesti) + taulukon solurakenne + validointi.

## Toimi näin (max 5 kohtaa)
1) Luo repo + perusrakenne ja yhteinen JSON-skeema
2) Toteuta **Step 00: PDF Probe & Route** (sivumanifesti)
3) Toteuta 2 pääpolkua: **Digital Pipeline** ja **Scan Pipeline**
4) Toteuta **Merge & Reading Order** + ankkurit
5) Toteuta **Normalisointi & QA** (summa-/tase-/ristiviite-tarkastukset) ja export (JSON+MD)

## Tarkistuslista (Fakta/Logiikka/Kieli)
- **Fakta:** Ei oleteta että koko PDF on yhtä tyyppiä; luokittelu tehdään sivukohtaisesti.
- **Logiikka:** OCR tehdään vain pakossa; taulukot käsitellään omana kanavanaan.
- **Kieli:** JSON-kentät nimetään yksiselitteisesti ja pidetään stabiileina (schema-first).

---

# 1) Repo ja hakemistorakenne (v1)

```
kuntatilinpaatos-parser/
  README.md
  pyproject.toml
  .env.example
  data/
    00_input/
      Kaupunki1_Tilinpaatos_2024.pdf
    10_work/
      page_manifest/
      pages_png/
      blocks_native/
      regions/
      tables_raw/
      debug/
  out/
    document.json
    document.md
    qa_report.json
  src/
    pipeline/
      config.py
      run_all.py
      step_00_pdf_probe.py
      step_10_native_text.py
      step_20_render_pages.py
      step_30_layout_regions.py
      step_40_vector_tables.py
      step_41_ocr_tables.py
      step_50_merge_reading_order.py
      step_60_normalize_validate.py
      step_70_export_md.py
    schemas/
      document_schema.json
      qa_schema.json
```

## V1-riippuvuudet (GPU-kiihdytys käytössä kun kannattaa)

### Perus (aina)
- PyMuPDF (fitz)
- pdfplumber / pdfminer.six
- pillow, opencv-python, numpy
- pandas
- pydantic, orjson
- rapidfuzz

### Renderöinti (scan/mixed/visual)
- **pdf2image + Poppler (suositus Windowsissa)**

### Taulukot (valinnainen)
- camelot-py[cv] (valinnainen) + tabula-py (valinnainen)

### Visuaalinen taulukkoparsinta (suositus vaativiin tilinpäätöksiin)
- **PaddleOCR PP-StructureV3** (table structure + PDF/image → structured)

### PaddleOCR-rooli v1: "Core OCR + Structure"
PaddleOCR otetaan stäkkiin, koska se kattaa käytännössä 3 kriittistä asiaa:
1) **Teksti-OCR** (tekstialueet, skannit)
2) **Taulukkorakenne** (PP-StructureV3 → HTML/Markdown/JSON-tyyppiset rakenteet)
3) **Dokumenttiparsinta** (PDF/image → strukturoitu output), jota voidaan käyttää joko pääpolkuna tai QA/diff-tarkoitukseen

Käyttöperiaate:
- `native`-sivuilla PaddleOCR:ää ei ajeta oletuksena (OCR on turha jos tekstikerros on kunnossa).
- `scan/mixed`-sivuilla PaddleOCR (PP-StructureV3) on ensisijainen taulukoille ja mahdollinen tekstialueille.
- MinerU säilyy rinnalla (ordering/regionit), mutta PaddleOCR hoitaa useimmiten **solurakenteen** parhaiten.


### OCR / DocAI (valinnainen)
- paddleocr (OCR + PP-StructureV3) tai pytesseract (fallback)
- MinerU (valinnainen, suositeltu dokumenttiparsintaan)
- **Dolphin-v2 (valinnainen VLM-dokumenttiparsija; page-level JSON+MD + element-level)**
- **MegaParse (valinnainen ingest/wrapper + benchmark + checkers)**

### MegaParse-rooli v1: "Ingestion wrapper + evaluator + checkers"
MegaParse otetaan mukaan *vain jos halutaan*:
- nopea moniformaattinen ingest (PDF/DOCX/PPTX jne.) ja "no information loss" -henkinen output
- valmiimpi **benchmark-harness** (similarity_ratio) ja vertailu muihin parsereihin
- **modulaariset checkers/postprocessing** -hookit (table checker + muut tarkistimet)
- valinnainen API-ajotapa (dev server)

Huomio: MegaParse Vision käyttää ulkoista multimodaalimallia (esim. GPT-4o/Claude) eli ei ole "puhtaasti open-source inference". Se pidetään erillisenä optiopolkuina, ei oletuksena.


### Dolphin-rooli v1: "Two-stage VLM parser (hard pages / QA-diff)"
Dolphin lisätään stäkkiin erityisesti tilanteisiin, joissa:
- sivu on **photographed/scan** tai layout on erittäin kompleksinen
- heuristiikka + PaddleOCR eivät tuota riittävän varmaa rakennetta
- halutaan **toinen riippumaton tulkinta** (diff/QA) lukemisjärjestyksestä ja elementeistä

Dolphin tarjoaa:
- **Stage 1:** dokumenttityypin luokittelu (digital vs photographed) + layout + reading order
- **Stage 2:** hybridiparsinta: holistic photographedille, elementtikohtainen rinnakkainen parsinta digitalille
- kaksi käyttötilaa: **page-level** (JSON+Markdown) ja **element-level** (table/formula/text/code)

### GPU/CUDA (kun saatavilla)
- PyTorch (CUDA build)
- PaddlePaddle GPU build (jos käytät PaddleOCR:ää CUDA:lla)
- **vLLM (valinnainen, Dolphin-kiihdytys)**
- **TensorRT-LLM (valinnainen, Dolphin-kiihdytys)**

> V1-periaate: **käytä GPU:ta aina kun se tuottaa nettohyödyn** (PP-StructureV3, OCR, MinerU/VLM/doc-parsing, raskaat kuvavaiheet). Natiivi PDF-tekstipoiminta ja vektoritaulukot ovat usein CPU:lla jo riittävän nopeita.
- pdfplumber / pdfminer.six
- pillow, opencv-python, numpy
- pandas
- pydantic, orjson
- rapidfuzz

### Taulukot (valinnainen)
- camelot-py[cv] (valinnainen) + tabula-py (valinnainen)

### OCR / DocAI (valinnainen)
- paddleocr (suositus OCR) tai pytesseract (fallback)
- **MinerU (valinnainen, suositeltu dokumenttiparsintaan)**

### GPU/CUDA (kun saatavilla)
- PyTorch (CUDA build)
- PaddlePaddle GPU build (jos käytät PaddleOCR:ää CUDA:lla)

> V1-periaate: **käytä GPU:ta aina kun se tuottaa nettohyödyn** (OCR/VLM/doc-parsing, raskaat kuvavaiheet). Natiivi PDF-tekstipoiminta ja vektoritaulukot ovat usein CPU:lla jo riittävän nopeita.

- PyMuPDF (fitz)
- pdfplumber / pdfminer.six
- pillow, opencv-python, numpy
- pandas
- pydantic, orjson
- rapidfuzz
- camelot-py[cv] (valinnainen) + tabula-py (valinnainen)
- paddleocr tai pytesseract (valinnainen OCR)
- **MinerU (valinnainen, suositeltu dokumenttiparsintaan)**

### MinerU-rooli v1: "Doc Parsing Accelerator (hybrid-auto-engine)"
MinerU tuodaan mukaan *vaihdettavana komponenttina* (ei lukita koko pinoa siihen), mutta hyödynnetään sen uusia backend-parannuksia.

MinerU Readme / 2.7.x oleelliset kohdat v1:een:
- Uusi **`hybrid` backend** yhdistää `pipeline` + `vlm` vahvuudet ja lisää laajennettavuutta.
- Oletusbackend on vaihtunut: **`hybrid-auto-engine`** (valitsee automaattisesti sopivan kiihdytysmoottorin ympäristön mukaan).
- `vlm/hybrid` backendit voivat **poimia tekstin suoraan text-PDF:stä**, vähentäen "parsing hallucinations".
- OCR tukee **109 kieltä** (asetetaan erikseen skannatuissa).
- Inline-formuloille on **erillinen kytkin**, joka voidaan disabloida jos ei tarvita (parantaa visuaalista laatua ja nopeutta).
- Automaattinen **EXIF-orientaation korjaus** input-kuville parantaa OCR-tuloksia.
- Tuottaa useita outputteja: NLP/Multimodal Markdown, reading-order JSON, sekä rikkaat intermediate-formaatit.
- Tarjoaa **layout/span-visualisoinnit** laadun nopeaan varmistukseen.
- Tukee CPU sekä GPU(CUDA)/NPU/MPS kiihdytystä.

Käyttöperiaate v1:
- `native` sivuilla: ensisijaisesti natiiviteksti + vektoritaulukot; MinerU voidaan ajaa **layout/order QA**-tarkoitukseen.
- `scan/mixed` sivuilla: MinerU `hybrid-auto-engine` voi tuottaa ordering+elementit ja osan sisällöstä; taulukon solut tarkennetaan edelleen PP-StructureV3:lla.

Asennusvinkki v1 (MinerU):
- Käytä "all backends" -asennusta, jotta optional-backendit tulevat mukaan: `uv pip install mineru[all]`.

MinerU tuodaan mukaan *vaihdettavana komponenttina* (ei lukita koko pinoa siihen):
- Tuottaa layout/reading-order -ehdotukset (blokit + järjestys) sekä usein myös taulukkoehdokkaita.
- Käytetään erityisesti `mixed`/`scan`-sivuilla, joissa heuristiikkalayout (Step 30) ei ole riittävä.
- MinerU:n output normalisoidaan samaan sisäiseen skeemaan (`blocks[]`, `tables[]`, `bbox`, `page_index`, `source`).

- PyMuPDF (fitz)
- pdfplumber / pdfminer.six
- pillow, opencv-python, numpy
- pandas
- pydantic, orjson
- rapidfuzz
- camelot-py[cv] (valinnainen) + tabula-py (valinnainen)
- paddleocr tai pytesseract (valinnainen OCR)

---

# 2) Step 00 — PDF Probe & Route (ydin)

## 2.0.0 Yhteiset järjestelmäriippuvuudet (Windows/Kone1)
- Poppler (pdf2image / PDF→PNG) — myös MegaParse edellyttää poppleria PDF/kuvatyössä.
- Tesseract (fallback OCR) — myös MegaParse mainitsee tesseractin asennuksen PDF/kuvatyössä.

---

## 2.0 GPU-kiihdytyksen valintalogiikka (v1)
Lisätään manifestiin laiteprofiili ja per-sivu suositus:
- `device_profile`: `{"cuda_available": bool, "gpu_name": str|null, "vram_gb": float|null}`
- `recommended_device`: `cpu | cuda`

Säännöt (v1):
- **GPU (cuda)** jos sivu on `scan` tai `mixed` ja seuraavia vaiheita käytetään: PP-StructureV3 (PaddleOCR), OCR, MinerU/VLM-parsing, raskas layout.
- **CPU** jos sivu on `native` ja käytetään vain natiivia tekstipoimintaa + vektoritaulukkoja.

Manifestiin kirjataan myös:
- `estimated_cost`: karkea arvio (render_dpi * sivut) → auttaa concurrency-asetuksissa.

---

## 2.0.1 Deterministinen mallien ja cachejen hallinta (v1 täsmäparannus)
Tavoite: **ei ad-hoc latauksia**, ei yllätyksiä, sama ajo tuottaa saman rakenteen ja debug-artefaktit.

### Yhtenäinen mallipolitiikka
- Kaikki mallit ja cachet ohjataan projektin sisään tai yhteen hallittuun kansioon.
- Pipeline saa aina `--model-dir <path>` ja kirjoittaa alihakemistoihin:
  - `models/paddleocr/`
  - `models/mineru/`
  - `models/dolphin/`
  - `models/megaparse/` (jos käytetään)
  - `cache/hf/` (jos käytetään HF-malleja)
  - `cache/paddle/`

### .env (pakolliset avaimet v1)
Lisää `.env` (ja `.env.example`) vähintään:
- `MODEL_DIR=./models`
- `CACHE_DIR=./cache`
- `PADDLEOCR_MODEL_DIR=./models/paddleocr`
- `MINERU_MODEL_DIR=./models/mineru`
- `DOLPHIN_MODEL_DIR=./models/dolphin`
- `MEGAPARSE_MODEL_DIR=./models/megaparse`
- `HF_HOME=./cache/hf`
- `TRANSFORMERS_CACHE=./cache/hf/transformers`
- `TORCH_HOME=./cache/torch`
- `PADDLE_HOME=./cache/paddle`
- `OCR_CACHE_DIR=./cache/ocr`

### Step 01 — Prepare Models & Assets (uusi)
Lisätään uusi vaihe ennen raskaita ajoja:
- `step_01_prepare_assets.py`
  - varmistaa hakemistot
  - lataa/validoi tarvittavat mallit paikallisesti (PaddleOCR/PP-StructureV3, mahdollinen MinerU/Dolphin)
  - varmistaa Poppler/Tesseract/JAVA/Ghostscript jos valitut polut niitä käyttävät
  - tekee “warmup”-testin (1 pieni ajo) ja kirjoittaa `data/10_work/debug/asset_check.json`

### Fail-fast laajennus
Jos `step_01_prepare_assets` epäonnistuu → stop ja raportoi:
- puuttuva malli
- väärä laite (CUDA/Paddle)
- puuttuva Poppler/JAVA/Ghostscript/Tesseract

---

## 2.1 Tavoite

## 2.0 GPU-kiihdytyksen valintalogiikka (v1)
Lisätään manifestiin laiteprofiili ja per-sivu suositus:
- `device_profile`: `{"cuda_available": bool, "gpu_name": str|null, "vram_gb": float|null}`
- `recommended_device`: `cpu | cuda`

Säännöt (v1):
- **GPU (cuda)** jos sivu on `scan` tai `mixed` ja seuraavia vaiheita käytetään: PP-StructureV3 (PaddleOCR), OCR, MinerU/VLM-parsing, raskas layout.
- **CPU** jos sivu on `native` ja käytetään vain natiivia tekstipoimintaa + vektoritaulukkoja.

Manifestiin kirjataan myös:
- `estimated_cost`: karkea arvio (render_dpi * sivut) → auttaa concurrency-asetuksissa.

---

## 2.0.1 Deterministinen mallien ja cachejen hallinta (v1 täsmäparannus)
Tavoite: **ei ad-hoc latauksia**, ei yllätyksiä, sama ajo tuottaa saman rakenteen ja debug-artefaktit.

### Yhtenäinen mallipolitiikka
- Kaikki mallit ja cachet ohjataan projektin sisään tai yhteen hallittuun kansioon.
- Pipeline saa aina `--model-dir <path>` ja kirjoittaa alihakemistoihin:
  - `models/paddleocr/`
  - `models/mineru/`
  - `cache/hf/` (jos käytetään HF-malleja)
  - `cache/paddle/`

### .env (pakolliset avaimet v1)
Lisää `.env` (ja `.env.example`) vähintään:
- `MODEL_DIR=./models`
- `CACHE_DIR=./cache`
- `PADDLEOCR_MODEL_DIR=./models/paddleocr`
- `MINERU_MODEL_DIR=./models/mineru`
- `HF_HOME=./cache/hf`
- `TRANSFORMERS_CACHE=./cache/hf/transformers`
- `TORCH_HOME=./cache/torch`
- `PADDLE_HOME=./cache/paddle`
- `OCR_CACHE_DIR=./cache/ocr`

### Step 01 — Prepare Models & Assets (uusi)
Lisätään uusi vaihe ennen raskaita ajoja:
- `step_01_prepare_assets.py`
  - varmistaa hakemistot
  - lataa/validoi tarvittavat mallit paikallisesti (PaddleOCR/PP-StructureV3, mahdollinen MinerU)
  - tekee “warmup”-testin (1 pieni ajo) ja kirjoittaa `data/10_work/debug/asset_check.json`

### Fail-fast laajennus
Jos `step_01_prepare_assets` epäonnistuu → stop ja raportoi:
- puuttuva malli
- väärä laite (CUDA/Paddle)
- puuttuva Poppler/JAVA/Ghostscript (jos käytössä)

---

## 2.1 Tavoite
Tuottaa `data/10_work/page_manifest/manifest.json`, jossa jokaiselle sivulle:
- `page_index`, `width`, `height`
- `native_text_chars` (natiivitekstin määrä)
- `text_blocks_count`
- `image_coverage_ratio` (kuvapinta-ala / sivu)
- `vector_line_density` (viivojen/vektorielementtien heuristiikka)
- `mode`: `native | scan | mixed`
- `recommended_dpi`
- `recommended_device`: `cpu | cuda`
- `notes` (debug)

## 2.2 Luokittelulogiiikka (deterministinen)
Käytetään useampaa signaalia:

### Signaalit
1) **Native text**
- Poimi lyhyt natiiviteksti (pdfplumber/PyMuPDF)
- `native_text_chars`

2) **Image coverage**
- PyMuPDF: listaa kuvat (`page.get_images(full=True)`) ja arvioi niiden bbox-pinta-ala
- vaihtoehtoisesti renderöi matalalla DPI:llä ja arvioi tekstin puuttumista + binäärikuva-alueita (vain jos pakko)

3) **Vector line density**
- PyMuPDF: tarkastele piirto-operaatioita (`page.get_drawings()`), laske viivojen määrä ja pituussumma (heuristiikka)

### Säännöt (v1)
- Jos `native_text_chars >= 300` ja `image_coverage_ratio < 0.40` → `mode=native`
- Jos `native_text_chars < 50` ja `image_coverage_ratio >= 0.60` → `mode=scan`
- Muuten → `mode=mixed`

### DPI-suositus
- `scan/mixed`: 300 DPI jos taulukkoepäily (vector_line_density korkea tai myöhemmin layout löytää taulukoita), muuten 200–250 DPI
- `native`: ei renderöidä oletuksena; renderöidään vain jos myöhemmissä vaiheissa havaitaan puuttuvia alueita

### Device-suositus
- jos `cuda_available` ja `mode in {scan, mixed}` → `recommended_device=cuda`
- muuten → `recommended_device=cpu`

## 2.3 Output-esimerkki (manifest.json)
```json
{
  "device_profile": {"cuda_available": true, "gpu_name": "RTX 4050", "vram_gb": 6.0},
  "pdf": {"filename": "Kaupunki1_Tilinpaatos_2024.pdf", "pages": 182},
  "pages": [
    {
      "page_index": 0,
      "native_text_chars": 842,
      "image_coverage_ratio": 0.12,
      "vector_line_density": 0.35,
      "mode": "native",
      "recommended_dpi": 0,
      "recommended_device": "cpu",
      "notes": ["text_ok"]
    },
    {
      "page_index": 17,
      "native_text_chars": 12,
      "image_coverage_ratio": 0.91,
      "vector_line_density": 0.02,
      "mode": "scan",
      "recommended_dpi": 300,
      "recommended_device": "cuda",
      "notes": ["scan_like"]
    }
  ]
}
```


## 2.1 Tavoite
Tuottaa `data/10_work/page_manifest/manifest.json`, jossa jokaiselle sivulle:
- `page_index`, `width`, `height`
- `native_text_chars` (natiivitekstin määrä)
- `text_blocks_count`
- `image_coverage_ratio` (kuvapinta-ala / sivu)
- `vector_line_density` (viivojen/vektorielementtien heuristiikka)
- `mode`: `native | scan | mixed`
- `recommended_dpi`
- `notes` (debug)

## 2.2 Luokittelulogiiikka (deterministinen)
Käytetään useampaa signaalia:

### Signaalit
1) **Native text**
- Poimi lyhyt natiiviteksti (pdfplumber/PyMuPDF)
- `native_text_chars`

2) **Image coverage**
- PyMuPDF: listaa kuvat (`page.get_images(full=True)`) ja arvioi niiden bbox-pinta-ala
- vaihtoehtoisesti renderöi matalalla DPI:llä ja arvioi tekstin puuttumista + binäärikuva-alueita (vain jos pakko)

3) **Vector line density**
- PyMuPDF: tarkastele piirto-operaatioita (`page.get_drawings()`), laske viivojen määrä ja pituussumma (heuristiikka)

### Säännöt (v1)
- Jos `native_text_chars >= 300` ja `image_coverage_ratio < 0.40` → `mode=native`
- Jos `native_text_chars < 50` ja `image_coverage_ratio >= 0.60` → `mode=scan`
- Muuten → `mode=mixed`

### DPI-suositus
- `scan/mixed`: 300 DPI jos taulukkoepäily (vector_line_density korkea tai myöhemmin layout löytää taulukoita), muuten 200–250 DPI
- `native`: ei renderöidä oletuksena; renderöidään vain jos myöhemmissä vaiheissa havaitaan puuttuvia alueita

## 2.3 Output-esimerkki (manifest.json)
```json
{
  "pdf": {"filename": "Kaupunki1_Tilinpaatos_2024.pdf", "pages": 182},
  "pages": [
    {
      "page_index": 0,
      "native_text_chars": 842,
      "image_coverage_ratio": 0.12,
      "vector_line_density": 0.35,
      "mode": "native",
      "recommended_dpi": 0,
      "notes": ["text_ok"]
    },
    {
      "page_index": 17,
      "native_text_chars": 12,
      "image_coverage_ratio": 0.91,
      "vector_line_density": 0.02,
      "mode": "scan",
      "recommended_dpi": 300,
      "notes": ["scan_like"]
    }
  ]
}
```

---

# 3) Kaksi pääpolkua (v1)

## 3.0 MinerU-integraatiotapa (valinnainen)
MinerU lisätään "sivukohtaiseksi kiihdyttimeksi" seuraavasti:
- **Vaihtoehto A (suositus): MinerU korvaa Step 30:n** tietyille sivuille: MinerU → `regions`/`blocks`/`reading_order` ehdotukset.
- **Vaihtoehto B: MinerU toimii toisena mielipiteenä** Step 30:n rinnalla (diff/QA): heuristiikka vs MinerU → jos ristiriita, liputa QA.
- **Vaihtoehto C: MinerU toimii koko dokumentille**, mutta lopputulos kulkee silti Step 50–70 läpi (merge, normalisointi, QA, export), jotta skeema ja tarkistukset pysyvät yhtenäisinä.

### Suositeltu backend (v1)
- Käytä MinerU:ssa oletuksena: **`hybrid-auto-engine`**.
- Jos haluat pakottaa:
  - `pipeline` (kevyempi/heuristinen)
  - `vlm` (tarkempi, mutta raskaampi)
  - `hybrid` (paras "out-of-the-box" konsistenssi)

MinerU:n käyttöperiaate v1:
1) Aja MinerU sivuille, joissa `mode in {scan, mixed}` tai joissa Step 30 epäonnistuu.
2) Jos sivu on text-PDF, anna MinerU:n poimia teksti natiivisti (vähentää hallucinaatiota), mutta **pidä Step 10 totuuden lähteenä** kun natiivi tekstipoiminta onnistuu.
3) Tuo MinerU:n löytämät elementit sisäiseen formaattiin:
   - `Block(type=text, bbox, text, source="mineru")`
   - `Table(bbox, cells?, source="mineru")`
4) Jos MinerU antaa taulukon vain alueena tai HTML:nä ilman luotettavaa solumäppäystä → Step 41A (PP-StructureV3) rakentaa solugridin.
5) Käytä MinerU:n **layout/span-visualisointeja** QA-debugissa (`debug/mineru_vis/`).

Lisäasetukset MinerU (v1):
- `--mineru-backend hybrid-auto-engine` (oletus)
- `--mineru-ocr-lang fin` (tai vastaava) skanneille
- `--mineru-inline-formula off` jos inline-LaTeX ei ole tarpeen
- `--mineru-visualize on` (layout/span)



---

## 3.0.1 Dolphin-integraatiotapa (valinnainen)
Dolphin lisätään v1:een erillisenä VLM-polkuna.

Käyttömallit:
- **A) QA/diff (suositus v1):** aja Dolphin vain sivuille, jotka QA liputtaa (low-confidence, sum/tase mismatch, layout epäselvä). Vertaa Dolphin page-level/element-level outputia omaan outputiin → jos ero, nosta severity.
- **B) Hard-pages fallback:** jos `mode=scan/mixed` ja PP-StructureV3 epäonnistuu tai antaa epävarman rakenteen, aja Dolphin page-level.
- **C) Layout-only boost:** aja Dolphin layout-only tuottamaan **reading order** ja elementtiboxit, mutta pidä sisältö ensisijaisesti: (digital) natiivi teksti + vektoritaulukot, (scan) PaddleOCR.

Tekniset huomiot:
- Dolphin tukee **multi-page PDF** -parsintaa.
- Dolphinissa on **max_batch_size** elementtidekoodauksen rinnakkaistukseen.
- Dolphin tarjoaa vLLM- ja TensorRT-LLM -tuet kiihdytykseen (valinnainen).

## 3.1 Digital Pipeline (mode=native)
**Tavoite:** maksimoida tarkkuus ilman OCR:ää.

### Step 10 — Native text blocks
- Poimi blokit bbox:llä
- Talleta JSONL: `blocks_native/page_XXXX.jsonl`
- Kentät: `page`, `block_id`, `text`, `bbox`, `font_stats`, `confidence=1.0`, `source=native`

### Step 40 — Vector tables
- Aja Camelot/Tabula sivuille, joilla on vahva taulukkosignaali (paljon viivoja tai teksti riveissä)
- Tulos: `tables_raw/vector_tables.jsonl`
- Kentät: `page`, `table_id`, `grid[c][r]`, `cells[]`, `bbox`, `source=vector`

### MinerU (valinnainen) digital-sivuilla
- Jos digital-sivulla reading-order on vaikea (monipalsta, sisennetyt elementit), MinerU voi tuottaa ordering-ehdotuksen.
- Tällöin MinerU:n ordering normalisoidaan Step 50:ssä, mutta **tekstisisältö otetaan edelleen natiivista** aina kun mahdollista.

### Step 20/30/41 (vain tarvittaessa)
- Jos `mixed` tai jos Step 10/40 havaitsee tyhjiä aukkoja → renderöi sivu ja tee alue-OCR vain puuttuville osille.

## 3.2 Scan Pipeline (mode=scan)
**Tavoite:** kuvapohjainen poiminta alueittain.

### Step 20 — Render pages
- Renderöi sivut PNG:ksi suositus-DPI:llä (pdf2image + Poppler suositus)

### Step 30 — Layout regions
- Etsi alueet: `table`, `text`, `figure`, `header`, `footer`
- Output: `regions/page_XXXX_regions.json`

### MinerU (valinnainen) scan-sivuilla
- MinerU voi korvata tai täydentää Step 30:a:
  - Jos käytössä: tallenna MinerU-alueet `regions/page_XXXX_regions.mineru.json`
  - Step 30 voi jäädä fallbackiksi.

### Step 41 — OCR tables + OCR text regions

#### 41A) Taulukot (ensisijainen)
- Leikkaa taulukkoalue (bbox)
- Aja **PaddleOCR PP-StructureV3** taulukkorakenteen tulkintaan
- Tallenna sekä:
  - `structure_html` / `structure_md` (jos saatavilla)
  - `cells[]` (r,c,text,value_num,unit,bbox,confidence)
- Jos PP-StructureV3 antaa vain rakenteen eikä luotettavia solu-bboxeja:
  - käytä OpenCV-viivagridiä + OCR soluihin fallbackina

#### 41B) Tekstialueet
- OCR alueeseen (PaddleOCR text) ja tallenna blokkeina

Output:
- `tables_raw/ocr_tables.jsonl`
- `blocks_ocr/page_XXXX.jsonl`
- debug: `debug/ppstructure_raw/` ja `debug/table_crops/`


## 3.4 Comprehensive Visual Tables (valinnainen, "vaikeat sivut" / koko dokumentti)
Kun tavoite on mahdollisimman korkea taulukkotarkkuus, lisätään erillinen "visuaalinen taulukkoparsinta" -polku:

- Renderöi sivut kuviksi (tyypillisesti 300 DPI)
- Piirrä taulukon viivagrid (OpenCV)
- Aja **PaddleOCR PP-StructureV3** taulukon rakenteen tulkintaan
- Aja domain-postprosessointi:
  - "palstataulut" → koordinaattipohjainen 3-sarakkeinen muoto (label / 2024 / 2023)
  - `table_fixer`-tyyppinen korjauskerros: headerit, sarakeankkurit, yhdistyneet solut

Käyttöperiaate v1:
- `mode=scan/mixed` sivuilla PP-StructureV3 on usein paras, kun taulukot ovat kuvina tai layout on sekava.
- `mode=native` sivuilla PP-StructureV3 voidaan ajaa vain "QA/diff"-tarkoitukseen tai yksittäisille vaikeille sivuille.

**Tavoite:** kuvapohjainen poiminta alueittain.

### Step 20 — Render pages
- Renderöi sivut PNG:ksi suositus-DPI:llä

### Step 30 — Layout regions
- Etsi alueet: `table`, `text`, `figure`, `header`, `footer`
- Output: `regions/page_XXXX_regions.json`

### MinerU (valinnainen) scan-sivuilla
- MinerU voi korvata tai täydentää Step 30:a:
  - Jos käytössä: tallenna MinerU-alueet `regions/page_XXXX_regions.mineru.json`
  - Step 30 voi jäädä fallbackiksi.

### Step 41 — OCR tables + OCR text regions
- Taulukot: leikkaa bbox → viivahaku → solugrid → OCR soluihin
- Tekstialueet: OCR alueeseen ja tallenna blokkeina
- Output: `tables_raw/ocr_tables.jsonl` ja `blocks_ocr/page_XXXX.jsonl`

## 3.3 Mixed Pipeline (mode=mixed)
**Tavoite:** yhdistää parhaat puolet.
- Native text + vector tables siltä osin kuin onnistuu
- Renderöinti + OCR vain niille alueille, joissa:
  - natiiviteksti puuttuu
  - taulukko ei irtoa vektorina
  - sivulla on kuvaskannattu liite
- MinerU (valinnainen): auttaa löytämään oikeat alueet ja lukemisjärjestyksen, erityisesti monimutkaisissa asetteluissa.


## 3.1 Digital Pipeline (mode=native)
**Tavoite:** maksimoida tarkkuus ilman OCR:ää.

### Step 10 — Native text blocks
- Poimi blokit bbox:llä
- Talleta JSONL: `blocks_native/page_XXXX.jsonl`
- Kentät: `page`, `block_id`, `text`, `bbox`, `font_stats`, `confidence=1.0`, `source=native`

### Step 40 — Vector tables
- Aja Camelot/Tabula sivuille, joilla on vahva taulukkosignaali (paljon viivoja tai teksti riveissä)
- Tulos: `tables_raw/vector_tables.jsonl`
- Kentät: `page`, `table_id`, `grid[c][r]`, `cells[]`, `bbox`, `source=vector`

### Step 20/30/41 (vain tarvittaessa)
- Jos `mixed` tai jos Step 10/40 havaitsee tyhjiä aukkoja → renderöi sivu ja tee alue-OCR vain puuttuville osille.

## 3.2 Scan Pipeline (mode=scan)
**Tavoite:** kuvapohjainen poiminta alueittain.

### Step 20 — Render pages
- Renderöi sivut PNG:ksi suositus-DPI:llä

### Step 30 — Layout regions
- Etsi alueet: `table`, `text`, `figure`, `header`, `footer`
- Output: `regions/page_XXXX_regions.json`

### Step 41 — OCR tables + OCR text regions
- Taulukot: leikkaa bbox → viivahaku → solugrid → OCR soluihin
- Tekstialueet: OCR alueeseen ja tallenna blokkeina
- Output: `tables_raw/ocr_tables.jsonl` ja `blocks_ocr/page_XXXX.jsonl`

## 3.3 Mixed Pipeline (mode=mixed)
**Tavoite:** yhdistää parhaat puolet.
- Native text + vector tables siltä osin kuin onnistuu
- Renderöinti + OCR vain niille alueille, joissa:
  - natiiviteksti puuttuu
  - taulukko ei irtoa vektorina
  - sivulla on kuvaskannattu liite

---

# 4) Merge & Reading Order (Step 50)

## 4.1 Yhdistämissäännöt
- Kaikki elementit esitetään yhteisessä muodossa: `blocks[]` ja `tables[]`
- Kaikilla on `bbox` ja `page_index`

## 4.2 Reading order (v1)
- Poista header/footer-alueet (region-tyypit tai ylä/ala-alueen heuristiikka)
- Järjestä blokit:
  1) sarakeklusterointi x-akselilla (1–2 palstaa)
  2) sisällä y-koordinaatin mukaan
- Ankkuroi taulukko siihen kohtaan, jossa sen bbox osuu lukemisjärjestyksessä

---

# 4.5 Semanttinen luokittelu (v1 lisäys)
Tavoite: tehdä dokumentista LLM:lle helpommin tulkittava siten, että jokaiselle sivulle, blokille ja taulukolle annetaan **semanttinen luokka** (ja mahdolliset aliluokat). Tämä ei korvaa poimintaa, vaan parantaa:
- hakua ("näytä tase-taulukot")
- QA:ta (taseeseen sovelletaan tase-checkerit, tuloslaskelmaan omat)
- LLM:n promptitusta (context routing)

## 4.5.1 Kaksitasoinen taksonomia

### (A) Layout-luokat (elementtitaso)
Käytetään DocLayNet-henkistä 11-luokan perusjaottelua:
- `title`
- `section_header`
- `text`
- `list_item`
- `table`
- `picture`
- `caption`
- `footnote`
- `formula`
- `page_header`
- `page_footer`

Nämä tulevat Step 30/MinerU/Dolphin -lähteistä ja normalisoidaan.

### (B) Financial-statement luokat (osio-/taulukkotaso)
Laaja mutta käytännöllinen luokittelu, joka kattaa sekä yritys- että kuntadokumentit:

**Primary statements**
- `balance_sheet` (statement of financial position / tase)
- `income_statement` (tuloslaskelma / toimintatuotot- ja kulut)
- `cash_flow_statement` (rahoituslaskelma / rahavirtalaskelma)
- `changes_in_equity` (oman pääoman muutokset, jos esitetään)

**Notes / disclosures**
- `notes` (liitetiedot yleistasolla)
- `accounting_policies` (tilinpäätöksen laatimisperiaatteet)
- `commitments_contingencies` (vastuut / sitoumukset)
- `related_party` (lähipiiri)

**Municipal-specific / report structure**
- `auditors_report` (tilintarkastuskertomus)
- `management_report` (toimintakertomus / katsaus)
- `budget_comparison` (talousarviovertailut)
- `performance_indicators` (tunnusluvut)
- `appendix` (liitteet)

## 4.5.2 Luokittelutapa (v1)
Käytä hybridiä: deterministiset säännöt + kevyt ML (valinnainen)

### Säännöt (pakolliset)
- Otsikkotekstin avainsanat (FI/EN), esim.
  - tase/balance sheet/statement of financial position
  - tuloslaskelma/income statement/profit or loss
  - rahoituslaskelma/cash flow
  - liitetiedot/notes
- Taulukon rakenneheuristiikat:
  - "2024/2023" sarakkeet + rivit "Vastaavaa/Vastattavaa" → `balance_sheet`
  - "Toimintatuotot/Toimintakulut/Verotulot" → `income_statement`
- Sivualueet: jos suurin osa elementeistä on `table`, sivuluokka painottuu taulukko-osioon

### ML (valinnainen)
- Kouluta/fine-tune layout-malli (DocLayNet-tyyppinen) vain jos Step 30+MinerU eivät riitä.
- Tekstiluokitin (esim. TF-IDF + linear) otsikoista/ensimmäisestä kappaleesta taulukkoluokan arvioon.

## 4.5.3 Output-kentät (lisätään document.json:iin)
- Page:
  - `page.semantic_section` (esim. `notes`)
  - `page.semantic_confidence`
- Block/Table:
  - `semantic_type` (layout-luokka)
  - `financial_type` (financial-statement luokka)
  - `classification_evidence[]` (lyhyet syyt: keyword/hint)

## 4.5.4 Uusi Step 55 (v1)
Lisää pipelineen:
- `step_55_semantic_classify.py`
  - syöte: draft `document.json` (Step 50)
  - tuotos: luokiteltu `document.json` + `debug/semantic_map.json`

---

# 5) Normalisointi & QA (Step 60) & QA (Step 60)

## 5.0 GPU-nopeutus (v1)
Normalisointi/QA on pääosin CPU-työtä, mutta v1:ssä varmistetaan suorituskyky ja hallittu rinnakkaisuus:

### Roolitus
- GPU: render (jos hyödyt), **PaddleOCR PP-StructureV3**, OCR, MinerU/VLM/doc-parsing, raskaat visuaaliset analyysit
- CPU: natiivi tekstipoiminta, vektoritaulukot, JSON/MD export, sum-checkit, ristiviitteet

### GPU-worker queue (v1 täsmäparannus)
Lisätään run_all:iin selkeä GPU-jono, joka estää VRAM-ylivuodot ja tekee ajosta deterministisen.

Suositus Kone1 (RTX 4050 6 GB):
- `GPU_CONCURRENCY=1` (oletus)
- `CPU_CONCURRENCY=6` (oletus)

### Backpressure ja batchaus
- Älä renderöi koko 200 sivua kerralla, jos et tarvitse: renderöi vain `scan/mixed` ja tarvittaessa taulukkoepäily-sivut.
- PP-StructureV3: aja **alueittain** (table crops) eikä koko sivua aina.
- Dolphin: pidä `max_batch_size` pienenä ja aja vain QA-needed sivuille.

---

## 5.0.1 Checkers-arkkitehtuuri (MegaParse-idea) (v1 parannus)
Lisätään v1:een MegaParse-henkinen **modulaarinen checker/postprocessing**-kerros:
- `checkers/`-hakemisto, jokainen checker palauttaa listan löydöksiä (`Finding[]`) ja voi tehdä korjausehdotuksia.

Pakolliset checkerit v1:
1) `SchemaChecker` (JSON schema / Pydantic)
2) `SemanticSectionChecker` (löytyykö primary statements, luokituksen kattavuus)
3) `TableCellChecker` (tyhjät solut, outlierit, epäparsittavat numerot)
4) `SumConsistencyChecker` (rivi/sarake-summat)
5) `BalanceSheetChecker` (vastaavaa/vastattavaa)
6) `CrossRefChecker` ("Liitetieto X")
7) `DiffChecker` (vector vs ocr vs mineru vs dolphin)

Kaikki checkers-ajot raportoidaan `qa_report.json`iin.

## 5.1 Normalisointi (pakollinen)
- Numerot: tuhaterottimet, desimaalit, miinus/sulkeet
- Yksiköt: `€`, `1 000 €`, `t€`, `%`
- Tekstin siistintä: rivinvaihdot, tavuviivat, monilyönnit

## 5.2 QA-tarkastukset (v1)
Tuota `out/qa_report.json`:
- `schema_valid`: document.json validi
- `table_cell_exactness`: tyhjät solut %, epäparsittavat numerot %
- `sum_checks`: löydetyt summa-rivit ja poikkeamat
- `balance_checks`: jos tase tunnistuu, testaa vastaavaa vs vastattavaa
- `xref_checks`: “Liitetieto X” esiintyy sekä pääosassa että liiteosassa
- `diff_checks`: jos samasta sisällöstä on useampi lähde (vector/ocr/dolphin), vertaile ja liputa erot

QA outputin pitää sisältää **täsmäpaikannus**:
- `page_index`, `block_id/table_id`, `bbox`, `reason`, `severity`

---

# 6) Export (Step 70)

## 5.0 GPU-nopeutus (v1)
Normalisointi/QA on pääosin CPU-työtä, mutta v1:ssä varmistetaan suorituskyky ja hallittu rinnakkaisuus:

### Roolitus
- GPU: render (jos hyödyt), **PaddleOCR PP-StructureV3**, OCR, MinerU/VLM/doc-parsing, raskaat visuaaliset analyysit
- CPU: natiivi tekstipoiminta, vektoritaulukot, JSON/MD export, sum-checkit, ristiviitteet

### GPU-worker queue (v1 täsmäparannus)
Lisätään run_all:iin selkeä GPU-jono, joka estää VRAM-ylivuodot ja tekee ajosta deterministisen.

Suositus Kone1 (RTX 4050 6 GB):
- `GPU_CONCURRENCY=1` (oletus)
- `CPU_CONCURRENCY=6` (oletus) — säädä oman CPU-kuorman mukaan

Käytännön toteutusperiaate:
- `ThreadPoolExecutor/ProcessPoolExecutor` CPU-tehtäville
- `GPU semaphore` (arvo 1) kaikille GPU-tehtäville
- GPU-tehtävät: `render(page)` (jos käytössä), `ppstructure(table_regions)`, `ocr(text_regions)`, `mineru(page)`
- CPU-tehtävät: `native_text(page)`, `vector_tables(page)`, `merge(page)`, `normalize_validate(document)`

### Backpressure ja batchaus
- Älä renderöi koko 200 sivua kerralla, jos et tarvitse: renderöi vain `scan/mixed` ja tarvittaessa taulukkoepäily-sivut.
- PP-StructureV3: aja **alueittain** (table crops) eikä koko sivua aina.

## 5.1 Normalisointi (pakollinen) (pakollinen)
- Numerot: tuhaterottimet, desimaalit, miinus/sulkeet
- Yksiköt: `€`, `1 000 €`, `t€`, `%`
- Tekstin siistintä: rivinvaihdot, tavuviivat, monilyönnit

## 5.2 QA-tarkastukset (v1)
Tuota `out/qa_report.json`:
- `schema_valid`: document.json validi
- `table_cell_exactness` (sisäinen): tyhjät solut %, epäparsittavat numerot %
- `sum_checks`: löydetyt summa-rivit ja poikkeamat
- `balance_checks`: jos tase tunnistuu (heuristiikka otsikoista), testaa vastaavaa vs vastattavaa
- `xref_checks`: “Liitetieto X” esiintyy sekä pääosassa että liiteosassa
- `diff_checks`: jos samasta taulukosta on sekä vector että ocr tulos, vertaile ja liputa erot

QA outputin pitää sisältää **täsmäpaikannus**:
- `page_index`, `block_id/table_id`, `bbox`, `reason`, `severity`

---

# 6) Export (Step 70)

## 5.1 Normalisointi (pakollinen)
- Numerot: tuhaterottimet, desimaalit, miinus/sulkeet
- Yksiköt: `€`, `1 000 €`, `t€`, `%`
- Tekstin siistintä: rivinvaihdot, tavuviivat, monilyönnit

## 5.2 QA-tarkastukset (v1)
Tuota `out/qa_report.json`:
- `schema_valid`: document.json validi
- `table_cell_exactness` (sisäinen): tyhjät solut %, epäparsittavat numerot %
- `sum_checks`: löydetyt summa-rivit ja poikkeamat
- `balance_checks`: jos tase tunnistuu (heuristiikka otsikoista), testaa vastaavaa vs vastattavaa
- `xref_checks`: “Liitetieto X” esiintyy sekä pääosassa että liiteosassa
- `diff_checks`: jos samasta taulukosta on sekä vector että ocr tulos, vertaile ja liputa erot

QA outputin pitää sisältää **täsmäpaikannus**:
- `page_index`, `block_id/table_id`, `bbox`, `reason`, `severity`

---

# 6) Export (Step 70)

## 6.1 document.json (rakenteinen)
- Pages → items (text/table/figure)
- Tables → cells (r,c, text_raw, value_num, unit, bbox, confidence)

## 6.2 document.md (LLM-luku)
- Otsikkohierarkia (heuristiikka fontti+isot kirjaimet+numerointi)
- Ankkurit: `[#p{page}_b{block}]`, `[#p{page}_t{table}]`
- Taulukot markdownina + säilytä myös linkki `table_id`

---

# 7) Definition of Done (v1)

1) `manifest.json` luokittelee sivut oikein vähintään karkean tasolla (native/scan/mixed) ja sisältää `recommended_device` (cpu/cuda)
2) `document.json` syntyy koko PDF:stä ja läpäisee skeeman
3) `document.md` syntyy ja sisältää taulukot + ankkurit
4) `qa_report.json` syntyy ja listaa ongelmakohdat sivu+alue -tasolla
5) Pipeline on ajettavissa yhdellä komennolla (run_all.py)
6) **Vaikeat taulukkosivut** voidaan ajaa erikseen "visual tables" -polulla (PP-StructureV3) ja tulos integroidaan samaan skeemaan

---

# 7.1 Fail-fast (v1)
Lisätään "fail-fast" tarkistus jo ennen raskaita ajoja:
- PDF avautuu, sivumäärä järkevä
- ensimmäiset 3 sivua: natiivi tekstipoiminta onnistuu (jos pitäisi)
- renderöinti onnistuu yhdelle testisivulle (Poppler OK)
- jos OCR-polku käytössä: Tesseract/PaddleOCR init OK
- jos GPU käytössä: `cuda_available` + Paddle/PyTorch device ok
- jos valinnaiset: MinerU/Dolphin init OK

Jos fail-fast epäonnistuu → stop ja tulosta selkeä syy.

---

# 7.2 Benchmark-harness (MegaParse-idea) (v1 parannus)
Lisätään v1:een oma benchmark-ajuri MegaParse-tyyliin:
- `evaluations/` + `evaluations/script.py`
- metriikka: **similarity_ratio** (tekstisisältö + rakenne), sekä meidän omat metrikat (cell exact match, sum-pass).

Tavoite:
- vertaile konfiguraatioita (native+vector vs ocr+ppstructure vs dolphin fallback) samalla testikorpuksella.


Lisätään "fail-fast" tarkistus jo ennen raskaita ajoja:
- PDF avautuu, sivumäärä järkevä
- ensimmäiset 3 sivua: natiivi tekstipoiminta onnistuu (jos pitäisi)
- renderöinti onnistuu yhdelle testisivulle
- jos GPU käytössä: `cuda_available` + Paddle/PyTorch device ok

Jos fail-fast epäonnistuu → stop ja tulosta selkeä syy.

1) `manifest.json` luokittelee sivut oikein vähintään karkean tasolla (native/scan/mixed)
2) `document.json` syntyy koko PDF:stä ja läpäisee skeeman
3) `document.md` syntyy ja sisältää taulukot + ankkurit
4) `qa_report.json` syntyy ja listaa ongelmakohdat sivu+alue -tasolla
5) Pipeline on ajettavissa yhdellä komennolla (run_all.py)

---

# 8) Cursor AI -työjonopromptit (v1)

## 8.1 Ensimmäinen toteutuserä
1) “Implement document_schema.json and Pydantic models for Document/Page/Block/Table/Cell/BBox.”
2) “Implement step_00_pdf_probe.py producing manifest.json with the rules above.”
3) “Implement run_all.py that reads manifest and runs per-mode steps with clear logging.”

## 8.2 Toinen toteutuserä
4) “Implement step_10_native_text.py extracting text blocks with bbox.”
5) “Implement step_20_render_pages.py rendering scan/mixed pages.”
6) “Implement step_30_layout_regions.py detecting table regions via OpenCV line detection.”

## 8.3 MinerU-lisäys (toteutetaan tässä kohtaa)
7) “Add optional MinerU runner: step_31_mineru_parse.py that can be enabled per page (scan/mixed) and outputs regions/blocks/ordering in a normalized JSON.”
8) “Update step_50_merge_reading_order.py to accept MinerU ordering as either primary or secondary opinion (diff/QA).”

## 8.3.1 Dolphin-lisäys (toteutetaan tässä kohtaa)
9) “Add optional Dolphin runner: step_32_dolphin_parse.py supporting page-level (JSON+MD) and element-level parsing; run only on selected pages (QA-needed) or as fallback for hard scan/mixed pages.”
10) “Update step_60_normalize_validate.py to ingest Dolphin outputs for diff/QA: reading order differences, table structure differences, and missing elements.”

## 8.4 Kolmas toteutuserä
11) “Implement step_40_vector_tables.py (Camelot/Tabula) and store cells.”
12) “Implement step_41_ocr_tables.py: PaddleOCR PP-StructureV3 first, then fallback grid+OCR; output cell grid.”
13) “Implement step_50_merge_reading_order.py.”
14) “Implement step_55_semantic_classify.py with the two-level taxonomy (layout + financial_type) and evidence.”
15) “Implement step_60_normalize_validate.py + step_70_export_md.py.”
9) “Implement step_40_vector_tables.py (Camelot/Tabula) and store cells.”
10) “Implement step_41_ocr_tables.py: crop, detect grid, OCR, output cell grid.”
11) “Implement step_50_merge_reading_order.py + step_60_normalize_validate.py + step_70_export_md.py.”

## 8.1 Ensimmäinen toteutuserä
1) “Implement document_schema.json and Pydantic models for Document/Page/Block/Table/Cell/BBox.”
2) “Implement step_00_pdf_probe.py producing manifest.json with the rules above.”
3) “Implement run_all.py that reads manifest and runs per-mode steps with clear logging.”

## 8.2 Toinen toteutuserä
4) “Implement step_10_native_text.py extracting text blocks with bbox.”
5) “Implement step_20_render_pages.py rendering scan/mixed pages.”
6) “Implement step_30_layout_regions.py detecting table regions via OpenCV line detection.”

## 8.3 Kolmas toteutuserä
7) “Implement step_40_vector_tables.py (Camelot/Tabula) and store cells.”
8) “Implement step_41_ocr_tables.py: crop, detect grid, OCR, output cell grid.”
9) “Implement step_50_merge_reading_order.py + step_60_normalize_validate.py + step_70_export_md.py.”

---

# 9) Käyttö (v1)

## 9.0 Mallien ja cachejen ohjaus (pakollinen täsmäparannus)
Aja aina mallipolut eksplisiittisesti:
- `--model-dir ./models --cache-dir ./cache`

Ensimmäinen ajokerta (asennus/valmistelu):
- `python -m src.pipeline.run_all --pdf data/00_input/Kaupunki1_Tilinpaatos_2024.pdf --prepare-assets --model-dir ./models --cache-dir ./cache`

## 9.1 Perusajo (automaattinen reititys)
Aseta PDF:
- `data/00_input/Kaupunki1_Tilinpaatos_2024.pdf`

Aja:
- `python -m src.pipeline.run_all --pdf data/00_input/Kaupunki1_Tilinpaatos_2024.pdf --model-dir ./models --cache-dir ./cache`

Tuotokset:
- `out/document.json`
- `out/document.md`
- `out/qa_report.json`

## 9.2 Visual tables (valinnainen)
Aja PP-StructureV3 vain tietyille sivuille (esim. vaikeat liitesivut):
- `python -m src.pipeline.run_all --pdf ... --visual-tables --visual-pages "151,152" --model-dir ./models --cache-dir ./cache`

Tai koko dokumentille:
- `python -m src.pipeline.run_all --pdf ... --comprehensive --model-dir ./models --cache-dir ./cache`

Lisäasetukset (suositus):
- `--model-dir <path>`: pidä mallit projektin sisällä ja vältä ad-hoc lataukset
- `--cache-dir <path>`: yhtenäinen cache
- `--device auto|cpu|cuda`: pakota laite tarvittaessa (manifesti suosittelee)
- `--gpu-concurrency 1` (RTX 4050 6 GB suositus)
- `--cpu-concurrency 6`

MinerU:
- `--mineru-backend hybrid-auto-engine`
- `--mineru-ocr-lang fin` (skannit)
- `--mineru-inline-formula off` (jos ei tarvita)
- `--mineru-visualize on`

Dolphin:
- `--dolphin-mode off|qa|fallback|layout-only`
- `--dolphin-max-batch-size 4` (Kone1 6 GB VRAM: aloita pienestä)
- `--dolphin-only-pages "17,18"` (valinnainen)

 "17,18"` (valinnainen, jos haluat ajaa vain tietyille sivuille)

`

## 9.3 Debug-artefaktit (v1)
Tallenna aina:
- renderöidyt sivut (`pages_png/`)
- MinerU-visualisoinnit (`debug/mineru_vis/`) (layout/span)
- taulukkoalueiden cropit (`debug/table_crops/`)
- taulukkoalueiden cropit (`debug/table_crops/`)
- grid/viivakuvat (`debug/grids/`)
- PP-StructureV3 raw-output (`debug/ppstructure_raw/`)
- asset-check (`debug/asset_check.json`)

Tämä nopeuttaa iterointia ja ongelmien paikantamista.

---

# 10) V1-rajoitteet (tiedossa)
- Layout-detectio on heuristinen (CPU-first). Se parannetaan myöhemmin vaihtamalla Step 30 “oppivaan” malliin ilman että muu stäkki muuttuu.
- Taulukon solugridin rakentaminen skanneista on vaikein kohta; QA liputtaa epävarmat.

---

# 11) V2-ideoita (ei toteuteta vielä)
- Layout-malli (DocLayNet-tyyppinen) CPU/GPU
- Parempi reading-order monipalstaisille sivuille
- Taulukkojen semanttinen luokittelu (Tase/Tuloslaskelma/Rahoituslaskelma/Liitetiedot)
- “Gold set” + regressiotestit

