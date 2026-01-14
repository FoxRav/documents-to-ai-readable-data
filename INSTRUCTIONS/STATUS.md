# Projektin Tila - PDF-tyyppireititin

## ✅ Toteutettu (Definition of Done)

### 1. Perusrakenne ✅
- [x] Repo-rakenne (data/, src/, checkers/, out/, models/, cache/)
- [x] pyproject.toml riippuvuuksineen
- [x] .env.example konfiguraatiotiedosto
- [x] .gitignore

### 2. JSON-skeemat ja Pydantic-mallit ✅
- [x] document_schema.json
- [x] qa_schema.json
- [x] models.py (Document, Page, Block, Table, Cell, BBox, jne.)

### 3. Pipeline-vaiheet ✅
- [x] step_01_prepare_assets.py - Mallien valmistelu ja fail-fast
- [x] step_00_pdf_probe.py - PDF-luokittelu ja manifest
- [x] step_10_native_text.py - Natiivi tekstipoiminta
- [x] step_20_render_pages.py - Sivujen renderöinti
- [x] step_30_layout_regions.py - Alueiden tunnistus (rinnakkaistettu)
- [x] step_40_vector_tables.py - Vektoritaulukot
- [x] step_41_ocr_tables.py - OCR-taulukot + OCR-tekstialueet (GPU-tuki)
- [x] step_50_merge_reading_order.py - Yhdistäminen ja lukemisjärjestys
- [x] step_55_semantic_classify.py - Semanttinen luokittelu
- [x] step_60_normalize_validate.py - Normalisointi ja QA
- [x] step_70_export_md.py - Markdown-export (ankkurit)

### 4. Pääajuri ✅
- [x] run_all.py - Orkestroi kaikki vaiheet
- [x] GPU-tuki (CUDA) OCR-vaiheessa
- [x] GPU-tiedot logitukseen

### 5. Checkers-arkkitehtuuri (osittain) ⚠️
- [x] base.py - Perusrajapinta
- [x] schema_checker.py - Skeeman validointi
- [x] sum_checker.py - Summatarkistukset
- [ ] semantic_section_checker.py - Puuttuu
- [ ] table_cell_checker.py - Puuttuu
- [ ] balance_sheet_checker.py - Puuttuu
- [ ] cross_ref_checker.py - Puuttuu
- [ ] diff_checker.py - Puuttuu

### 6. Definition of Done -tarkistus

1. ✅ `manifest.json` luokittelee sivut (native/scan/mixed) ja sisältää `recommended_device`
2. ✅ `document.json` syntyy koko PDF:stä (toteutettu, mutta tyhjä koska OCR ei löytänyt dataa)
3. ✅ `document.md` syntyy ja sisältää ankkurit (toteutettu)
4. ⚠️ `qa_report.json` syntyy mutta puuttuvia checkereitä
5. ✅ Pipeline ajettavissa yhdellä komennolla (run_all.py)
6. ⚠️ Visual tables -polku ei ole toteutettu (valinnainen)

## ⚠️ Tunnistetut ongelmat

### Ongelma 1: Tyhjä document.json
- **Syy**: Kaikki sivut luokiteltiin "scan"-tyyppisiksi, mutta:
  - Step 10 ei aja scan-sivuille → ei natiivi-tekstiä
  - Step 41 OCR ei löytänyt taulukoita/tekstiä oikein
- **Korjaus**: Lisätty OCR-tekstialueiden poiminta Step 41:een
- **Status**: Korjattu koodissa, vaatii uuden ajokierroksen

### Ongelma 2: Puuttuvia QA-checkereitä
- **Puuttuu**: 5 checkerit (SemanticSectionChecker, TableCellChecker, BalanceSheetChecker, CrossRefChecker, DiffChecker)
- **Status**: Toteutettava

### Ongelma 3: GPU-worker queue
- **Puuttuu**: GPU semaphore run_all.py:hen estämään VRAM-ylivuodot
- **Status**: Toteutettava

## 📋 Seuraavat vaiheet

1. **Täydennä puuttuvat QA-checkerit** (5 kpl)
2. **Toteuta GPU-worker queue** (semaphore)
3. **Testaa pipeline uudelleen** OCR-tekstialueiden kanssa
4. **Tarkista että document.json sisältää dataa** (ei tyhjä)
5. **Varmista että qa_report.json sisältää kaikki kentät**

## 🔧 Tekniset korjaukset tehty

- ✅ Lisätty OCR-tekstialueiden poiminta Step 41:een (41B)
- ✅ GPU-tuki PaddleOCR:lle
- ✅ Rinnakkaistettu alueiden tunnistus
- ✅ NumPy 1.26.4 yhteensopivuus PaddleOCR:n kanssa
- ✅ Ankkurit document.md:hen

## 📊 Testitilanne

- **PDF**: Lapua-Tilinpaatos-2024.pdf (154 sivua)
- **Luokittelu**: Kaikki 154 sivua "scan"
- **Renderöinti**: ✅ 154 PNG luotu
- **Alueiden tunnistus**: ✅ 136/154 käsitelty (rinnakkaisesti)
- **Lopputulokset**: document.json, document.md, qa_report.json luotu (mutta tyhjiä)
