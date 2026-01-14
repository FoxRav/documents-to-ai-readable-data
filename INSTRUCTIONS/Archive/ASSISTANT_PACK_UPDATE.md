# Cursor-ohje | assistant-pack liitteiden päivitys (F:\-DEV-\36.PDF-tyyppireititin\assistant-pack)

## Tarkoitus
`assistant-pack/` on **uudelleenkäytettävä prompt-työkalupakki** Cursor/LLM-työskentelyn vakioimiseksi. Päivitykset tehdään hallitusti, jotta:
- globaali ohjeistus ei "saastu" projektikohtaisilla asioilla
- projektikohtainen konteksti pysyy ajan tasalla
- muutokset ovat pieniä, katselmoitavia ja testattavia

---

# 1) Mitä tiedostoja päivitetään ja milloin

## 1.1 assistant-pack (harvoin muuttuva)
Polku: `F:\-DEV-\36.PDF-tyyppireititin\assistant-pack\`

Tiedostot:
- `SESSION_BOOTSTRAP_GLOBAL.md` — **vakio työtapa + vastauskontrakti** (muutokset harvinaisia)
- `PROJECT_CONTEXT_TEMPLATE.md` — **pohja** projektikohtaiselle kontekstille (muutokset harvinaisia)
- `INIT_SESSION.md` — aloitusprompti (pakottaa ymmärrys/plan/first patch)
- `RESET_PROMPT.md` — palauttaa työskentelyn minimi-diff + verifiointi -tilaan
- `README_Carefully.md` — käyttöohje + päivitysrytmi
- `CHANGELOG.md` — mitä muuttui ja miksi

**Päivitä assistant-packia vain, jos muutos hyödyttää useita projekteja.**

## 1.2 Projektikohtainen konteksti (usein muuttuva)
Polku: `F:\-DEV-\36.PDF-tyyppireititin\PROJECT_CONTEXT.md` (tai vastaava projektin juuressa)

**Päivitä projektikontekstia aina kun:**
- arkkitehtuuri/teknologiavalinta muuttuu
- DoD muuttuu
- riippuvuudet, testit, CI/CD, lint/format, työkaluvalinnat muuttuvat
- löytyy uusi tunnettu bugi/rajoite
- lisätään regression anchor (golden file / testi / verifiointikomento)

---

# 2) Päivitysprosessi (pieni diff, yksi asia kerrallaan)

## 2.1 Käytännön sääntö
- Yksi muutoskategoria per commit (esim. "Update INIT_SESSION contract" tai "Add checker list to README")
- Älä tee laajoja refaktorointeja samalla

## 2.2 Työjärjestys
1) Tee muutos yhteen tiedostoon
2) Päivitä `assistant-pack/CHANGELOG.md` (Unreleased → Added/Changed/Fixed)
3) Tee nopea tarkistus (diff) ja "smoke"
4) Commit

---

# 3) PowerShell-komennot (Kone1)

Avaa repo:
```powershell
cd "F:\-DEV-\36.PDF-tyyppireititin"
```

Tarkista tila:
```powershell
git status
```

Näytä muutokset:
```powershell
git diff
```

Commit (pienellä ja kuvaavalla viestillä):
```powershell
git add assistant-pack\SESSION_BOOTSTRAP_GLOBAL.md assistant-pack\CHANGELOG.md
# tai lisää vain muuttuneet tiedostot

git commit -m "assistant-pack: tighten init contract"
```

---

# 4) Miten päivitetään projektin liitteet / kopiot

## 4.1 Uusi projekti (suositus)
1) Kopioi `assistant-pack/PROJECT_CONTEXT_TEMPLATE.md` → projektin juureen nimellä `PROJECT_CONTEXT.md`
2) Täytä `PROJECT_CONTEXT.md` projektikohtaisilla asioilla

PowerShell:
```powershell
Copy-Item .\assistant-pack\PROJECT_CONTEXT_TEMPLATE.md .\PROJECT_CONTEXT.md
```

## 4.2 Olemassa oleva projekti
- Älä muokkaa templatea projektikohtaiseksi.
- Päivitä vain `PROJECT_CONTEXT.md`.

---

# 5) Cursor-käyttö (copy/paste -järjestys)

Uusi chat / uusi tehtävä Cursorissa — liitä tässä järjestyksessä:
1) `assistant-pack/SESSION_BOOTSTRAP_GLOBAL.md`
2) `<projekti>/PROJECT_CONTEXT.md`
3) `assistant-pack/INIT_SESSION.md`
4) Tehtäväkuvaus

Kun laatu alkaa heiketä (turhia refaktoreita, arvailua, ei verifiointia):
- liitä `assistant-pack/RESET_PROMPT.md`

---

# 6) Päivitysten laatuvaatimukset (Definition of Done liitteille)

Kun päivität assistant-packia, varmista:
- Teksti on yksiselitteinen (ei ristiriitaisia ohjeita)
- Ohjeet eivät ole projektispesifejä (ne kuuluvat `PROJECT_CONTEXT.md`:iin)
- Ohjeissa on aina vähintään:
  - työtapa / rajoitteet
  - vastauskontrakti (järjestys)
  - minimal diff + verifiointi -periaate
- `CHANGELOG.md` päivitetty

---

# 7) Suositeltu versiointityyli (kevyt)

`assistant-pack/CHANGELOG.md`:
- Pidä `Unreleased`-osio
- Lisää alakohdat: Added / Changed / Fixed
- Yksi rivi per muutos

---

# 8) Nopea tarkistuslista ennen pushia

- [ ] `git diff` näyttää vain aiotut muutokset
- [ ] `CHANGELOG.md` päivitetty
- [ ] Et lisännyt projektikohtaisia detaljeja global-packiin
- [ ] Ohjeet ovat ajettavissa (komennot/polut oikein)

