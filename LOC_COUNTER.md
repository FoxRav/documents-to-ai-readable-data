# LOC Counter - Lines of Code Laskuri

Tämä työkalu laskee repositorion koodimäärän (LOC) ja tuottaa raportin.

## Nopea alku

**Aja repojuuresta:**

```bash
# Linux/macOS
python3 tools/loc_counter.py --root .

# Windows
python tools/loc_counter.py --root .
```

Jos `loc_counter.py` on juuressa tai muualla, käytä oikeaa polkua:

```bash
python loc_counter.py --root .
```

## Käyttö

### Peruskäyttö

```bash
# Skannaa nykyinen hakemisto (oletus)
python tools/loc_counter.py

# Skannaa tietty hakemisto
python tools/loc_counter.py --root /path/to/repo

# Käytä .gitignore-tiedostoa poissulkemiseen
python tools/loc_counter.py --use-gitignore

# Määritä raportin tallennuspolku
python tools/loc_counter.py --out custom/path/report.md
```

### Parametrit

- `--root <path>`: Skannattava hakemisto (oletus: `.` = nykyinen hakemisto)
- `--use-gitignore`: Käytä `.gitignore`-tiedostoa poissulkemiseen (vaatii `pathspec`-paketin)
- `--out <path>`: Raportin tallennuspolku (oletus: `<root>/reports/loc_report.md`)

### Esimerkit

```bash
# Skannaa nykyinen hakemisto
python tools/loc_counter.py

# Skannaa toinen hakemisto
python tools/loc_counter.py --root ../other-repo

# Käytä gitignorea ja tallenna mukautettuun paikkaan
python tools/loc_counter.py --use-gitignore --out my_report.md

# Skannaa testihakemisto
python tools/loc_counter.py --root tests/fixture_small
```

## Raportti

Raportti tallennetaan oletuksena `reports/loc_report.md` ja sisältää:

- **Yhteenveto**: Total Code LOC, Non-empty LOC, Comments, Blanks
- **Kielikohtaiset taulukot**: Molemmille metriikoille (Code LOC ja Non-empty LOC)
- **Kategorisointi**: code / data / docs
- **TOP-20 tiedostot**: Sekä Code LOC että Non-empty LOC mukaan
- **Poissuljetut hakemistot/tiedostot**: Lista mitä jätettiin pois

### Metriikat

1. **Code LOC**: Pelkät koodirivit (ei kommentteja, ei tyhjiä)
2. **Non-empty LOC**: Koodi + kommentit (ei tyhjiä)

## Tuen kielet

- Python, JavaScript, TypeScript, Go, Java, C#, C++, C, Rust, Ruby, PHP, Kotlin, Swift
- SQL, Shell, PowerShell
- YAML, TOML, JSON, Markdown, XML, HTML, CSS

## Kommenttien tunnistus

- **Python/Shell/YAML**: `#` kommentit
- **C/C++/Java/JS/TS/Go/Rust/PHP**: `//` ja `/* */` kommentit
- **SQL**: `--` kommentit
- **HTML/XML**: `<!-- -->` kommentit
- **JSON/Markdown**: Ei kommenttien tunnistusta

## Poissuljetut hakemistot/tiedostot

Seuraavat jätetään automaattisesti pois:

**Hakemistot:**
- `node_modules/`, `dist/`, `build/`, `.next/`, `.nuxt/`, `.cache/`
- `.venv/`, `venv/`, `__pycache__/`, `.git/`
- `coverage/`, `target/`, `out/`, `.turbo/`
- `.idea/`, `.vscode/`, `.pytest_cache/`

**Tiedostot:**
- `*.min.*`, `*.map`
- `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`, `Pipfile.lock`

**Binääritiedostot:**
- PDF, PNG, JPG, ZIP, EXE, DLL, jne.

## Vaatimukset

- Python 3.10+
- Valinnainen: `pathspec` paketti (jos haluat käyttää `--use-gitignore`)

```bash
pip install pathspec
```

## Huomioita

- Työkalu on **repo-agnostinen**: se toimii missä tahansa repossa
- Komento raportissa rakennetaan automaattisesti `sys.argv[0]`:sta
- Jos `scc` tai `tokei` on saatavilla, ne ovat parempia vaihtoehtoja
- Tämä on fallback-toteutus kun muita työkaluja ei ole saatavilla

## Ongelmatilanteet

**"Root directory does not exist"**
- Tarkista että `--root` polku on oikein
- Käytä absoluuttista polkua jos tarvetta

**"No files found"**
- Tarkista että hakemisto sisältää kooditiedostoja
- Tarkista poissuljettujen hakemistojen lista

**Gitignore ei toimi**
- Asenna `pathspec`: `pip install pathspec`
- Tai käytä ilman `--use-gitignore` lippua

## Lisätietoja

Katso myös:
- `tools/loc_counter.py` - Lähdekoodi
- `tests/test_loc_counter.py` - Yksikkötestit
- `reports/loc_report.md` - Esimerkkiraportti
