# Changelog

Všechny významné změny v tomto projektu budou zdokumentovány v tomto souboru.

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
