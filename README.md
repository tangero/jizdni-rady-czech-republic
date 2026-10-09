# Jízdní řády České republiky - GTFS Dataset

Agregovaná a konsolidovaná data veřejné dopravy v České republice ve standardním GTFS formátu.

## 📊 Přehled datasetu

Tento dataset obsahuje jízdní řády městské hromadné dopravy (MHD), regionálních autobusů a vlaků v České republice ve standardním GTFS formátu. Páteřním zdrojem jsou oficiální data Celostátního informačního systému o jízdních řádech (CIS JŘ), která zahrnují i Pražskou integrovanou dopravu. Tato data jsou primárně veřejnou službou, veřejná a pro veřejnost určená.

**Stav dat: 9. 10. 2026** (zdroj CIS JŘ publikovaný 9. 10. 2026)

### Pokrytí

- **241 dopravců**
- **36,937 zastávek** (deduplikovaných podle názvu, 99 % s GPS souřadnicemi)
- **6,140 linek** (4,196 MHD + 1,944 regionálních)
- **289,357 spojů** (244,800 MHD + 44,557 regionálních)
- **5.2 milionu stop_times záznamů**

## 🗂️ Struktura dat

Všechny tři datasety mají stejnou sadu souborů a jsou samostatně použitelné:

| Soubor | Obsah |
|--------|-------|
| `agency.txt` | dopravci (společné pro všechny datasety) |
| `stops.txt` | zastávky s GPS souřadnicemi (společné) |
| `routes.txt` | linky |
| `trips.txt` | spoje |
| `calendar.txt` | pravidelná platnost spojů (dny v týdnu, od–do) |
| `calendar_dates.txt` | výjimky z platnosti (svátky, výluky, jednotlivé dny) |
| `stop_times.txt.gz` | příjezdy a odjezdy na zastávkách (gzip) |

### data/mhd/
Městská hromadná doprava: tramvaje, metro, trolejbusy, lanovky, přívozy a autobusy s nejvýše trojmístným číslem linky. 4,196 linek, 244,800 spojů, 4.6 mil. stop_times (37 MB komprimováno).

### data/regional/
Regionální a dálkové spoje: vlaky a meziměstské autobusy. 1,944 linek, 44,557 spojů, 0.6 mil. stop_times (4 MB komprimováno).

### data/merged/
Kompletní integrovaný dataset (MHD + regionální) pro použití v aplikacích. 6,140 linek, 289,357 spojů, 5.2 mil. stop_times (42 MB komprimováno).

> **Pozor na dělení MHD / regionální:** rozdělení je heuristické podle typu dopravy a čísla linky. Regionální autobusové linky integrovaných systémů s trojmístným číslem (např. PID 3xx–7xx, ODIS 3xx) proto spadají do `mhd/`. Pro routing používejte `merged/`.

## 📋 Statistiky

### Typ dopravy (merged)

| Typ | GTFS route_type | Počet linek |
|-----|-----------------|-------------|
| Tramvaj | 0 | 95 |
| Metro | 1 | 3 (Praha) |
| Vlak | 2 | 1,309 |
| Autobus | 3 | 4,601 |
| Přívoz | 4 | 5 |
| Lanovka | 7 | 2 |
| Trolejbus | 11 | 125 |

## 🚀 Použití

### Poznámka o komprimovaných souborech

Velké `stop_times.txt` soubory jsou komprimované gzipem (`.txt.gz`) kvůli limitům GitHubu. GTFS specifikace oficiálně podporuje gzip komprimované soubory a většina nástrojů je automaticky dekomprimuje.

**Dekomprese (pokud potřebuješ nekomprimované soubory):**
```bash
gunzip -k data/merged/stop_times.txt.gz
```

### Rychlý start

```python
import csv
import gzip

# Načtení zastávek (nekomprimované)
with open('data/mhd/stops.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    stops = list(reader)
    print(f"Nalezeno {len(stops)} zastávek")

# Načtení linek (nekomprimované)
with open('data/mhd/routes.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    routes = list(reader)
    print(f"Nalezeno {len(routes)} linek")

# Načtení stop_times (komprimované - přímé čtení)
with gzip.open('data/mhd/stop_times.txt.gz', 'rt', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    # Zpracuj po řádcích pro úsporu paměti
    for row in reader:
        print(row['trip_id'], row['stop_id'])
        break  # Příklad - ukaž jen první řádek
```

### Import do databáze

```bash
# PostgreSQL s PostGIS
createdb transit_cz
psql transit_cz < import_gtfs.sql

# SQLite
sqlite3 transit.db < import_gtfs.sql
```

### Vizualizace

Použijte standardní GTFS nástroje:
- [GTFS Viewer](https://github.com/vasile/GTFS-viz)
- [Transitland](https://www.transit.land/)
- [OpenTripPlanner](https://www.opentripplanner.org/)

## 📖 GTFS Formát

Tento dataset používá standardní [GTFS (General Transit Feed Specification)](https://gtfs.org/) formát.

### Základní soubory

#### agency.txt
Dopravní agentury provozující linky.
```
agency_id,agency_name,agency_url,agency_timezone,agency_lang
AGENCY_MHD,Městská hromadná doprava,http://example.com,Europe/Prague,cs
```

#### stops.txt
Zastávky a stanice.
```
stop_id,stop_name,stop_lat,stop_lon
MHD_STOP_0,Hlavní nádraží,0.0,0.0
```

#### routes.txt
Dopravní linky.
```
route_id,agency_id,route_short_name,route_long_name,route_type
MHD_ROUTE_0,AGENCY_MHD,Pardubice,MHD Pardubice,3
```

#### trips.txt
Jednotlivé spoje na lince.
```
trip_id,route_id,service_id
MHD_TRIP_0,MHD_ROUTE_0,SV_2
```

#### stop_times.txt
Časy příjezdů a odjezdů na zastávkách.
```
trip_id,stop_id,stop_sequence,arrival_time,departure_time
MHD_TRIP_0,MHD_STOP_0,1,08:00:00,08:00:00
```

#### calendar.txt
Kalendář platnosti jízdních řádů.
```
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
SV_2,1,1,1,1,1,1,1,20261017,20261018
```

## ⚠️ Omezení

### GPS souřadnice
Souřadnice zastávek pocházejí z CIS JŘ. Zhruba 1 % zastávek (353) souřadnice nemá a má nastaveno `0.0, 0.0`.

Zastávky jsou deduplikované podle názvu (formát „Obec, zastávka“), takže jednotlivá nástupiště téže zastávky jsou sloučena do jednoho bodu.

### Časové pokrytí
Dataset obsahuje jen spoje, které jedou v den sestavení nebo později (starší jsou vyřazeny). Skutečné pokrytí závisí na tom, jak daleko dopředu dopravci publikují:

| Den | Jedoucích spojů |
|-----|-----------------|
| středa 14. 10. 2026 | 159,559 |
| středa 4. 11. 2026 | 109,348 |
| středa 9. 12. 2026 | 101,929 |
| středa 16. 12. 2026 | 20,403 |

PID publikuje jízdní řády zhruba dva týdny dopředu a 13. 12. 2026 proběhne celostátní změna jízdních řádů. Data je proto vhodné pravidelně aktualizovat (viz níže).

### Rozsah dat
Pokrytí odpovídá CIS JŘ: vlaky, linková autobusová doprava a MHD, kterou dopravci do CIS JŘ předávají.

## 🔧 Nástroje pro práci s GTFS

### Validace
- [GTFS Validator](https://github.com/MobilityData/gtfs-validator)
- [FeedValidator](https://github.com/google/transitfeed)

### Analýza
- [gtfs-kit](https://github.com/mrcagney/gtfs_kit)
- [gtfs-to-geojson](https://github.com/node-gtfs/gtfs-to-geojson)

### Routing
- [OpenTripPlanner](https://www.opentripplanner.org/)
- [Valhalla](https://github.com/valhalla/valhalla)

## 📊 Zdroje dat

| Zdroj | URL | Použití |
|-------|-----|---------|
| **CIS JŘ** (Celostátní informační systém o jízdních řádech) | https://www.spojenka.cz/jrdata/jizdnirady-gtfs.zip | páteřní zdroj, obsahuje i PID a MHD měst |
| **PID** (Pražská integrovaná doprava) | https://data.pid.cz/PID_GTFS.zip | volitelně (`--with-pid`); CIS JŘ už PID obsahuje, zapnutí vede k duplicitám |
| **IDOS KOMPLET.ZIP** (CHAPS) | https://www.chaps.cz/cs/download/idos#kotvatt | volitelně (`--with-tt`), heuristicky dekódovaný binární formát bez GPS |

Všechna ID jsou přemapována na jednotné schéma (`AG_*`, `ST_*`, `RT_*`, `TR_*`, `SV_*`). ID nejsou mezi verzemi stabilní.

## 📄 Licence

Dataset je poskytován pod licencí **CC BY 4.0** (Creative Commons Attribution 4.0 International).

Můžete data:
- ✅ Sdílet - kopírovat a distribuovat
- ✅ Upravovat - remixovat, transformovat, využívat pro další práci
- ✅ Komerčně využívat

Za podmínek:
- **Uvedení autora** - Musíte uvést odkaz na tento zdroj, tedy zpracovatele Patricka Zandla a na internetu použít proklik na Github repozitář. 

## 🔄 Vlastní aktualizace dat

Data si můžete aktualizovat sami. Stačí Python 3.9+ bez externích závislostí.

### Postup

```bash
# 1. Stažení aktuálních zdrojů do data/sources/ (CIS JŘ ~80 MB, PID ~50 MB)
python scripts/download_sources.py

# 2. Integrace do data/mhd, data/regional, data/merged (cca 1 minuta)
python scripts/integrate_all_data_fast.py

# 3. Kontrola konzistence
python scripts/validate_gtfs.py
```

Užitečné volby integrace:

```bash
# Ponechat spoje platné od konkrétního data (default: dnes)
python scripts/integrate_all_data_fast.py --from-date 20261213

# Přidat data z IDOS KOMPLET.ZIP (nejdřív je převeďte, viz níže)
python scripts/integrate_all_data_fast.py --with-tt
```

### Volitelně: konverze IDOS KOMPLET.ZIP

1. Stáhněte KOMPLET.ZIP z [CHAPS/IDOS](https://www.chaps.cz/cs/download/idos#kotvatt) a rozbalte ho
2. Spusťte `python scripts/convert_tt_to_gtfs.py /cesta/ke/KOMPLET --integrate`

Konverzní pipeline dekóduje binární .tt soubory (`tt_decoder_v2.py`), odfiltruje POI, servisní texty a interní CHAPS kódy, převede data do GTFS (`komplet_to_gtfs.py`) a s `--integrate` je přidá k CIS JŘ. Dekodér je heuristický, data nemají GPS souřadnice a mají obecný kalendář (pracovní dny).

```
KOMPLET/
├── Data1/    # Vlaky (VL)
├── Data2/    # Meziměstské autobusy (BUS)
└── Data3/    # Městská MHD (MHD)
```

### Skripty v repo

| Skript | Popis |
|--------|-------|
| `scripts/download_sources.py` | Stažení aktuálních GTFS zdrojů (CIS JŘ, PID) |
| `scripts/integrate_all_data_fast.py` | Integrace zdrojů do výstupních datasetů |
| `scripts/validate_gtfs.py` | Kontrola referenční integrity a časového pokrytí |
| `scripts/convert_tt_to_gtfs.py` | Konverze IDOS KOMPLET.ZIP (volitelné) |
| `scripts/tt_decoder_v2.py` | Dekodér CHAPS .tt binárního formátu |
| `scripts/komplet_to_gtfs.py` | Konvertor dekódovaných dat do GTFS |

## 🤝 Přispívání

Uvítáme příspěvky v oblasti:
- Doplnění GPS souřadnic zastávek
- Aktualizace jízdních řádů
- Rozšíření pokrytí o další města
- Opravy chyb v datech

## 📞 Kontakt

Pro otázky ohledně datasetu vytvořte issue na GitHubu.

## 🙏 Poděkování

Tento dataset vznikl jako součást projektu [Přijímačky na školu](https://www.prijimackynaskolu.cz) pro analýzu dostupnosti středních škol veřejnou dopravou. A pak jsem si říkal, že když už jsem si s tím dal tolik práce a spálil tolik procesorového času OrchestrAI nástroje pro utřídění dat, tak by se to mohlo hodit i ostatním. 

---

**Verze:** 2.2.0
**Poslední aktualizace:** 2026-10-09
**Formát:** GTFS (General Transit Feed Specification)
**Velikost datasetu:** ~150 MB (komprimované stop_times)
**Zdroje:** CIS JŘ (GTFS), volitelně PID a IDOS KOMPLET
