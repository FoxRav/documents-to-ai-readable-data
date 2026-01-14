# GitHub Push Checklist

> **📖 Katso myös:** `GITHUB_SETUP.md` - Yksityiskohtaiset ohjeet GitHub-repositorion luomiseen

## ✅ Tarkistettu ja valmisteltu

### 1. Salaisuudet ja arkaluontoinen data
- ✅ `.env` tiedosto on `.gitignore`-listalla
- ✅ `.env.example` on mukana (ei salaisuuksia)
- ✅ Ei API-avaimia, salasanoja tai tokeneita koodissa
- ✅ Kaikki salaisuudet käyttävät `.env`-tiedostoa

### 2. .gitignore päivitetty
Seuraavat hakemistot/tiedostot on poissuljettu:
- ✅ `.env` ja kaikki `.env.*` (paitsi `.env.example`)
- ✅ `data/00_input/*.pdf`, `*.jpg`, `*.jpeg`, `*.png` (arkaluontoinen testidata)
- ✅ `data/10_work/` (väliaikaiset työtiedostot)
- ✅ `out/` (generoidut tulostiedostot)
- ✅ `models/` (latautuvat mallit)
- ✅ `cache/` (välimuisti)
- ✅ `reports/` (generoidut raportit)
- ✅ `tmp/` (väliaikaiset tiedostot)
- ✅ `*.log` (lokitiedostot)
- ✅ `__pycache__/`, `*.pyc` (Python välimuisti)
- ✅ `venv/`, `.venv` (virtuaaliympäristöt)
- ✅ `.vscode/`, `.idea/` (IDE-asetukset)

### 3. Generoidut tiedostot
- ✅ `data/00_input/*/music/` (OMR-tulokset)
- ✅ `data/00_input/*/omr_output/` (OMR-tulokset)
- ✅ `data/00_input/*/debug/` (debug-kuvat)
- ✅ `data/00_input/*_output.json` ja `*_output.md` (generoidut tulokset)

### 4. Dokumentaatio
- ✅ `README.md` päivitetty projektin nimeksi "Documents to AI-Readable Data"
- ✅ `LOC_COUNTER.md` lisätty
- ✅ Kaikki dokumentaatiotiedostot mukana

### 5. Koodi
- ✅ Ei kovakoodattuja salaisuuksia
- ✅ Kaikki konfiguraatio käyttää `.env`-tiedostoa
- ✅ Type hints ja koodityyli seurataan

## 📋 Ennen pushausta

1. **Tarkista git status:**
   ```bash
   git status
   ```

2. **Varmista että .env ei ole staged:**
   ```bash
   git status --short | findstr ".env"
   ```
   (Ei pitäisi näkyä `.env` tiedostoa)

3. **Tarkista että .env.example on staged:**
   ```bash
   git status --short | findstr ".env.example"
   ```
   (Pitäisi näkyä `.env.example`)

4. **Lisää kaikki muutokset:**
   ```bash
   git add .
   ```

5. **Tarkista vielä kerran mitä lisätään:**
   ```bash
   git status
   ```

6. **Commit:**
   ```bash
   git commit -m "Update project name and prepare for GitHub"
   ```

7. **Push:**
   ```bash
   git push origin main
   ```
   (tai `master` jos käytät sitä)

## ⚠️ Varoitukset

- **ÄLÄ** puskaa `.env`-tiedostoa
- **ÄLÄ** puskaa PDF-tiedostoja `data/00_input/` hakemistosta
- **ÄLÄ** puskaa generoituja raportteja `reports/` hakemistosta
- **ÄLÄ** puskaa väliaikaisia tiedostoja `tmp/` hakemistosta

## 🔍 Viimeinen tarkistus

Ennen pushausta, aja:
```bash
# Tarkista että .env ei ole staged
git diff --cached --name-only | findstr ".env"

# Tarkista että .env.example on staged
git diff --cached --name-only | findstr ".env.example"

# Listaa kaikki staged-tiedostot
git diff --cached --name-only
```

Jos `.env` näkyy staged-tiedostoissa, poista se:
```bash
git reset HEAD .env
```
