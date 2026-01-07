# Prompt-paketti: SESSION BOOTSTRAP + INIT + RESET

## Mikä tämä on
Tämä repo sisältää pienen prompt-paketin, jonka tarkoitus on tehdä Cursor/LLM-työskentelystä toistettavaa ja vähentää "vaihteleva kehittäjä" -ilmiötä uusissa chateissa.

Paketti pakottaa mallin:
- noudattamaan samoja työskentelysääntöjä (ei arvailua, minimi-diff)
- vastaamaan aina samalla rakenteella (ymmärrys → suunnitelma → muutokset → verifiointi → riskit)
- pysymään pienissä, katselmoitavissa muutoksissa
- palautumaan takaisin raiteille, jos se alkaa ehdottaa ylimääräisiä refaktoreita

## Tiedostot ja roolit

### 1) SESSION_BOOTSTRAP.md
**Rooli:** "Työsopimus" mallin kanssa (pysyvä perusrunko).
Sisältää:
- rooli ja työskentelysäännöt
- projektin täytettävä tiivistelmä (kohdat 1–9)
- output contract (vastausjärjestys)
- DoD (Definition of Done)
- testankkurit ja päätösloki

**Käyttö:** Liitä uuden chatin alkuun ja täytä projektikohtaiset kohdat 1–9.

### 2) INIT_SESSION.md
**Rooli:** Aloitusprompti, joka pakottaa mallin ensin suunnittelemaan ennen koodaamista.
Pakottaa muodon:
- Understanding (max 5 bullet)
- Assumptions (vain jos pakko)
- Plan (max 7 bullet)
- First patch (minimal diff)

**Käyttö:** Liitä SESSION_BOOTSTRAP:n jälkeen uuden chatin alussa.

### 3) RESET_PROMPT.md
**Rooli:** Hätäjarru / "takaisin raiteille" -prompti, kun malli alkaa:
- arvailla
- laajentaa scopea
- ehdottaa tarpeettomia refaktoreita
- rikkoa rajapintoja
- unohtaa verifioinnin

**Käyttö:** Liitä sellaisenaan chattiin, kun laatu droppaa.

## Suositeltu käyttöpolku (uusi chat)
Liitä chattiin tässä järjestyksessä:
1) `SESSION_BOOTSTRAP.md` (täytettynä kohtien 1–9 osalta)
2) `INIT_SESSION.md`

Sen jälkeen anna varsinainen tehtävä.

## Miten tämä "elää" projektin edetessä
Älä tee SESSION_BOOTSTRAP:sta projektikohtaista sekasotkua. Pidä kaksi periaatetta:

1) **Pysyvä osa** (harvoin muuttuva)
- työskentelysäännöt
- vastausformaatti
- "minimi-diff" ja verifiointi

2) **Projektikohtainen osa** (muuttuva)
- kohdat 1–9 (Project summary, Current state, Tech stack, Repo boundaries, DoD, testit, päätösloki)
- nämä täytetään ja päivitetään projektin aikana

### Päivitysrytmi (ei "joka 5 prompt")
Päivitä projektikohtaisia kohtia aina kun tapahtuu jokin näistä:
- tehtiin merkittävä arkkitehtuuri/teknologiapäätös
- muuttui DoD / acceptance criteria
- lisättiin riippuvuus, lint, testit tai CI
- löytyi uusi regressio/bugi tai tunnettu rajoite
- milestone/julkaisu valmistui

Käytännössä: päivitys "tapahtumista", ei promptimäärästä.

## Päätösloki (Decision log)
Pidä kohta 9 ajantasalla.
Kirjaa jokaisesta merkittävästä päätöksestä:
- päivämäärä
- päätös
- lyhyt perustelu
Tämä estää mallia keksimästä "uusia suuntia" joka chatissa.

## Do / Don't

### DO
- vaadi suunnitelma ennen koodia (INIT_SESSION)
- vaadi minimi-diff ja verifiointi joka tehtävään
- pidä "DO NOT touch" -lista ajan tasalla
- päivitä testankkurit (golden queries/fixtures), jotta regressiot huomataan

### DON'T
- älä laajenna scopea kesken tehtävän ilman eksplisiittistä pyyntöä
- älä anna mallin tehdä isoja refaktoreita "varmuuden vuoksi"
- älä hyväksy koodia ilman verifiointikomentoja ja odotettua tulosta

## Quick commands (kopioitavat)
### Start new chat
1) Paste: SESSION_BOOTSTRAP (filled)
2) Paste: INIT_SESSION
3) Paste your task

### Reset when off-rails
Paste: RESET_PROMPT

## Encoding-vaatimus
Kaikki tässä paketissa olevat .md-tiedostot tallennetaan **UTF-8 with BOM** -muodossa (Windows-yhteensopivuus).

