# GitHub Push - Korjausohjeet

## Ongelma 1: Haara on "master", ei "main"

Sinulla on kaksi vaihtoehtoa:

### Vaihtoehto A: Pushaa master-haaraan (Helpoin)

```powershell
# Pushaa master-haaraan
git push -u origin master
```

### Vaihtoehto B: Nimeä haara uudelleen main:ksi

```powershell
# Nimeä haara uudelleen
git branch -M main

# Pushaa main-haaraan
git push -u origin main
```

## Ongelma 2: Remote URL on placeholder

Sinun täytyy korvata placeholder oikealla GitHub-repository URL:lla.

### Tarkista nykyinen remote

```powershell
git remote -v
```

### Päivitä remote URL

**Korvaa `<username>` ja `<repo-name>` omilla arvoillasi:**

```powershell
# Poista vanha remote
git remote remove origin

# Lisää oikea remote URL
# Esimerkki: git remote add origin https://github.com/johndoe/documents-to-ai-readable-data.git
git remote add origin https://github.com/<username>/<repo-name>.git

# Tarkista
git remote -v
```

## Nopea korjaus (yhdessä)

```powershell
# 1. Päivitä remote URL (korvaa omalla URL:llasi!)
git remote set-url origin https://github.com/<username>/<repo-name>.git

# 2. Tarkista
git remote -v

# 3. Pushaa master-haaraan
git push -u origin master
```

## Jos haluat käyttää "main" haaraa

```powershell
# 1. Päivitä remote URL
git remote set-url origin https://github.com/<username>/<repo-name>.git

# 2. Nimeä haara uudelleen
git branch -M main

# 3. Pushaa
git push -u origin main
```

## Tarkista että push onnistui

```powershell
# Tarkista remote-status
git remote show origin

# Tarkista että olet synkronoitu
git status
```

Mene myös GitHub-repositorysi URL:ään ja varmista että kaikki tiedostot näkyvät.
