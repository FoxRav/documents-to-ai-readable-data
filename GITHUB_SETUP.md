# GitHub Repository Setup Guide

## 1. Luo GitHub Repository

### Vaihtoehto A: GitHub Web-selaimessa

1. **Kirjaudu GitHubiin**: Mene [github.com](https://github.com) ja kirjaudu sisään

2. **Luo uusi repository**:
   - Klikkaa oikeasta yläkulmasta **"+"** → **"New repository"**
   - Täytä tiedot:
     - **Repository name**: `documents-to-ai-readable-data` (tai haluamasi nimi)
     - **Description**: `Production-ready document and image parsing pipeline that converts PDFs and images into structured, AI-readable data`
     - **Visibility**: 
       - ✅ **Public** (jos haluat avoimen lähdekoodin)
       - ✅ **Private** (jos haluat yksityisen repon)
     - **ÄLÄ** valitse:
       - ❌ "Add a README file" (sinulla on jo README.md)
       - ❌ "Add .gitignore" (sinulla on jo .gitignore)
       - ❌ "Choose a license" (sinulla on jo LICENSE)
   - Klikkaa **"Create repository"**

3. **Kopioi repository URL**:
   - GitHub näyttää ohjeet, kopioi **HTTPS** tai **SSH** URL
   - Esimerkki: `https://github.com/kayttajanimi/documents-to-ai-readable-data.git`

### Vaihtoehto B: GitHub CLI (gh)

```bash
# Asenna GitHub CLI jos ei ole asennettuna
# Windows: winget install GitHub.cli

# Kirjaudu sisään
gh auth login

# Luo repository
gh repo create documents-to-ai-readable-data \
  --description "Production-ready document and image parsing pipeline that converts PDFs and images into structured, AI-readable data" \
  --public  # tai --private
```

## 2. Yhdistä Paikallinen Repo GitHubiin

### Tarkista nykyinen git-status

```powershell
# Tarkista että olet oikeassa hakemistossa
cd f:\-DEV-\36.PDF-tyyppireititin

# Tarkista git-status
git status
```

### Lisää Remote Repository

```powershell
# Lisää GitHub-repository remote-osoitteeksi
# Korvaa <username> ja <repo-name> omilla arvoillasi
git remote add origin https://github.com/<username>/<repo-name>.git

# Tarkista että remote lisättiin oikein
git remote -v
```

**Esimerkki:**
```powershell
git remote add origin https://github.com/johndoe/documents-to-ai-readable-data.git
```

### Jos remote on jo olemassa

Jos `origin` on jo määritelty, voit:
1. **Poistaa vanhan**:
   ```powershell
   git remote remove origin
   git remote add origin https://github.com/<username>/<repo-name>.git
   ```

2. **Tai päivittää URL:n**:
   ```powershell
   git remote set-url origin https://github.com/<username>/<repo-name>.git
   ```

## 3. Valmistele Commit

### Tarkista mitä lisätään

```powershell
# Näytä kaikki muutokset
git status

# Näytä yksityiskohtaisemmin
git status --short
```

### Varmista että .env EI ole staged

```powershell
# Tarkista staged-tiedostot
git diff --cached --name-only | Select-String ".env"

# Jos .env näkyy, poista se:
git reset HEAD .env
```

### Lisää kaikki tiedostot

```powershell
# Lisää kaikki uudet ja muutetut tiedostot
git add .

# Tarkista vielä kerran
git status
```

### Tarkista .gitignore toimii

```powershell
# Tarkista että .env on gitignoressa
git check-ignore .env
# Pitäisi tulostaa: .env

# Tarkista että .env.example EI ole gitignoressa
git check-ignore .env.example
# Ei pitäisi tulostaa mitään
```

## 4. Tee Ensimmäinen Commit

```powershell
# Tee commit
git commit -m "Initial commit: Documents to AI-Readable Data pipeline

- PDF processing (digital, scanned, mixed) with adaptive OCR
- Image processing (music sheet OMR, document OCR)
- Full pipeline with QA validation
- Comprehensive documentation"
```

**Vaihtoehtoinen commit-viesti:**
```powershell
git commit -m "Initial commit: Production-ready document and image parsing pipeline"
```

## 5. Push GitHubiin

### Ensimmäinen push

```powershell
# Push main-haaraan (tai master jos käytät sitä)
git push -u origin main
```

**Jos käytät `master`-haaraa:**
```powershell
git push -u origin master
```

**Jos saat virheen "main branch does not exist":**
```powershell
# Tarkista nykyinen haara
git branch

# Jos olet master-haarassa, joko:
# 1) Nimeä haara uudelleen
git branch -M main
git push -u origin main

# TAI 2) Pushaa master-haaraan
git push -u origin master
```

### Jos saat virheen "failed to push"

**Virhe: "remote: Support for password authentication was removed"**
- Ratkaisu: Käytä **Personal Access Token** (PAT) salasanan sijaan
- Luo PAT: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Käytä tokenia salasanan sijaan

**Virhe: "Permission denied"**
- Tarkista että olet kirjautunut oikeaan GitHub-tiliin
- Tarkista että sinulla on oikeudet repositoryyn

## 6. Varmista Push Onnistui

### Tarkista GitHubissa

1. Mene GitHub-repositorysi URL:ään
2. Varmista että kaikki tiedostot näkyvät
3. Tarkista että `.env` **EI** näy tiedostoissa
4. Tarkista että `.env.example` **näkyy** tiedostoissa

### Tarkista paikallisesti

```powershell
# Tarkista remote-status
git remote show origin

# Tarkista että olet synkronoitu
git status
```

## 7. Aseta Repository Asetukset (Valinnainen)

### Lisää Topics/Tags

GitHub-repositorion sivulla:
1. Klikkaa **⚙️ Settings** (tai **About**-osio)
2. Lisää **Topics**: `python`, `ocr`, `pdf-parsing`, `document-processing`, `ai`, `music-notation`, `omr`

### Lisää Description

GitHub-repositorion sivulla:
- Klikkaa **⚙️ Settings**
- Päivitä **Description**: `Production-ready document and image parsing pipeline that converts PDFs and images (JPG/PNG) into structured, AI-readable data (JSON + Markdown)`

### Aseta Default Branch Protection (Valinnainen)

Jos haluat suojata `main`-haaran:
1. Settings → Branches
2. Add rule for `main`
3. Valitse: "Require pull request reviews before merging"

## 8. Seuraavat Askeleet

### Lisää README Badges (Valinnainen)

Voit lisätä README.md:hen badgeja:

```markdown
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen.svg)
```

### Lisää GitHub Actions CI/CD (Valinnainen)

Luo `.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e .
      - run: pytest  # kun testit on valmiina
```

## 9. Tärkeät Turvallisuushuomiot

### ✅ Tarkistettu

- ✅ `.env` on `.gitignore`-listalla
- ✅ Ei salaisuuksia koodissa
- ✅ `.env.example` on mukana (ei salaisuuksia)

### ⚠️ Muista

- **ÄLÄ** puskaa `.env`-tiedostoa
- **ÄLÄ** puskaa PDF-tiedostoja `data/00_input/` hakemistosta
- **ÄLÄ** puskaa generoituja raportteja
- Jos vahingossa puskaat salaisuuksia:
  1. Poista ne GitHubista
  2. Vaihda salaisuudet (API-avaimet, salasanat)
  3. Tarkista git-historia: `git log --all --full-history -- .env`

## 10. Yhteenveto Komentoja

```powershell
# 1. Tarkista status
cd f:\-DEV-\36.PDF-tyyppireititin
git status

# 2. Lisää remote (korvaa URL omalla)
git remote add origin https://github.com/<username>/<repo-name>.git

# 3. Lisää tiedostot
git add .

# 4. Tarkista että .env ei ole mukana
git status --short | Select-String ".env"

# 5. Commit
git commit -m "Initial commit: Documents to AI-Readable Data pipeline"

# 6. Push
git push -u origin main
```

## Ongelmatilanteet

### "fatal: remote origin already exists"
```powershell
git remote remove origin
git remote add origin https://github.com/<username>/<repo-name>.git
```

### "error: failed to push some refs"
```powershell
# Hae ensin remote-muutokset
git pull origin main --allow-unrelated-histories

# Sitten push
git push -u origin main
```

### "Authentication failed"
- Käytä **Personal Access Token** (PAT) salasanan sijaan
- Tai aseta SSH-avaimet: `gh auth login`

## Lisätietoja

- [GitHub Docs: Creating a new repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
- [GitHub Docs: Adding a remote](https://docs.github.com/en/get-started/getting-started-with-git/managing-remote-repositories)
- [GitHub Docs: Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
