# Changelog

Všechny významné změny v tomto projektu budou zdokumentovány v tomto souboru.

## [2.2.0] - 2026-10-09

### Přidáno
- `scripts/download_sources.py`: stažení aktuálních zdrojů (CIS JŘ, PID) do `data/sources/`
- `scripts/validate_gtfs.py`: kontrola referenční integrity a časového pokrytí, volba `--min-trips`
- GitHub Action `update-data.yml`: týdenní aktualizace s validací, publikace jako Release, měsíční commit do `main`
- `calendar.txt` a `calendar_dates.txt` ve všech třech datasetech
- `data/regional/stop_times.txt.gz` (dříve v repozitáři chyběl)

### Opraveno
- **Platnost spojů**: obsah `calendar.txt` se do výstupu nezapisoval, většina spojů odkazovala na nedefinované `service_id`
- **Nekonzistentní stop_times**: `stop_times.txt.gz` se vytváří přímo při integraci, nemůže tedy zůstat z jiného sestavení
- **Duplicitní spoje PID**: CIS JŘ už obsahuje PID, samostatný PID zdroj je proto jen volitelný (`--with-pid`)
- **Souřadnice zastávek**: CIS JŘ se načítá první, takže zastávky z TT konverze bez GPS už nepřepisují skutečné souřadnice
- Duplicitní `service_id` ve zdrojovém `calendar.txt` se mapují jen jednou

### Změněno
- Aktualizována data z CIS JŘ k 9. 10. 2026
- Výchozím zdrojem je pouze CIS JŘ; PID (`--with-pid`) a TT konverze (`--with-tt`) jsou volitelné
- Vyřazují se spoje, které od data sestavení už nejedou (`--from-date`), a nepoužité zastávky, linky a dopravci
- Cesty ke zdrojům jsou konfigurovatelné, integrace už nečte data z jiného repozitáře
- Trolejbusy (`route_type` 11) se řadí do MHD

## [2.1.0] - 2026-02-21

### Přidáno
- **Self-contained TT konvertor**: Skripty pro konverzi CHAPS .tt souborů přímo v tomto repo
  - `scripts/tt_decoder_v2.py` — dekodér binárního .tt formátu
  - `scripts/komplet_to_gtfs.py` — konvertor dekódovaných dat do GTFS
  - `scripts/convert_tt_to_gtfs.py` — hlavní workflow skript pro konverzi a integraci
- **Pole `agency_id` v stops.txt**: Každá zastávka je přiřazena k příslušné agentuře (AGENCY_VL/BUS/MHD)

### Opraveno
- **Filtrování nesmyslných zastávek**: Odstraněny POI záznamy (bankomaty, banky), německé/anglické servisní texty (legendy), CHAPS interní kódy (`¤¤J775001-3`), markup tagy (`{L}`, `{l}`) a geografické zóny (`*UA`, `*CZ-KA`)
- **Cross-reference filtrování**: Zastávky nereferencované v žádném spoji jsou automaticky odstraněny

### Změněno
- Aktualizována data z nového KOMPLET balíku (2026-02)
- Integrační skript nyní čte TT data z `data/tt_source/ALL/` (odděleno od výstupu)
- Aktualizován .gitignore pro logy a mezivýstupy konverze

## [2.0.0] - 2026-02-08

### Přidáno
- **Integrace GTFS_CR dat**: Přidána kompletní data z oficiálního Celostátního informačního systému o jízdních řádech (portal.cisjr.cz)
- **Integrace PID dat**: Přidána data Pražské integrované dopravy
- **Deduplikace zastávek**: Zastávky jsou nyní deduplikovány podle názvu napříč všemi zdroji
- **Kategorizace linek**: Linky jsou automaticky kategorizovány na MHD a regionální podle typu dopravy a kontextu
- **Kalendářní výjimky**: Přidáno 1.58 mil. kalendářních výjimek (svátky, prázdniny, víkendy)
- **Tři výstupní datasety**:
  - `data/mhd/` - pouze městská hromadná doprava
  - `data/regional/` - pouze regionální a dálková doprava
  - `data/merged/` - kompletní integrovaný dataset

### Změněno
- **Navýšení pokrytí**: Z 18,862 na 61,052 zastávek
- **Navýšení linek**: Z 116 na 6,735 linek
- **Navýšení spojů**: Z 15,121 na 384,685 spojů
- **Navýšení agentur**: Z 3 na 215 dopravních agentur
- **Unified ID schéma**: Všechna ID byla přemapována na unified schéma (AG_*, ST_*, RT_*, TR_*, SV_*)

### Technické detaily
- Implementován optimalizovaný integrační skript s streaming processingem pro velké soubory
- Stop times zpracovány průběžně bez načítání do paměti (celkem 6.9 mil. záznamů)
- Kategorizace MHD vs. regionální založena na route_type a kontextu (číslo linky, název, typ)

## [1.0.0] - 2026-02-08

### Přidáno
- Počáteční verze datasetu s MHD daty pro 109 měst
- 18,862 zastávek
- 116 linek
- 15,121 spojů
- Základní GTFS soubory (agency, stops, routes, trips, stop_times, calendar)
- Dokumentace (README, USAGE, DATA_QUALITY)
- CC BY 4.0 licence

---

**Formát:** [Keep a Changelog](https://keepachangelog.com/)
**Verzování:** [Semantic Versioning](https://semver.org/)
