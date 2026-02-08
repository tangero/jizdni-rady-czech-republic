# Jízdní řády České republiky - GTFS Dataset

Agregovaná a konsolidovaná data veřejné dopravy v České republice ve standardním GTFS formátu.

## 📊 Přehled datasetu

Tento dataset obsahuje kompletní informace o jízdních řádech městské hromadné dopravy (MHD) a regionálních spojích v České republice, integrující data z více veřejně dostupných zdrojů.

### Pokrytí

- **215 dopravních agentur**
- **61,052 unikátních zastávek**
- **6,735 dopravních linek** (4,588 MHD + 2,147 regionálních)
- **384,685 denních spojů** (301,953 MHD + 82,732 regionálních)
- **6.9 milionu stop_times záznamů**

## 🗂️ Struktura dat

### data/mhd/
Městská hromadná doprava (MHD) pro města po celé České republice.

**Standardní GTFS soubory:**
- `agency.txt` - 215 dopravních agentur
- `stops.txt` - 61,052 zastávek
- `routes.txt` - 4,588 MHD linek (tramvaje, metro, městské autobusy)
- `trips.txt` - 301,953 spojů
- `stop_times.txt.gz` - 5.9 mil. záznamů příjezdů/odjezdů (45 MB komprimováno, 226 MB nekomprimováno)

### data/regional/
Regionální a dálkové spoje (vlaky, meziměstské autobusy).

**Standardní GTFS soubory:**
- `agency.txt` - 215 dopravních agentur (sdílené)
- `stops.txt` - 61,052 zastávek (sdílené)
- `routes.txt` - 2,147 regionálních linek
- `trips.txt` - 82,732 spojů
- `stop_times.txt` - 1.0 mil. záznamů příjezdů/odjezdů (39 MB nekomprimováno)

### data/merged/
Kompletní integrovaný dataset (MHD + regionální) pro použití v aplikacích.

**Obsahuje:**
- Vše výše zmíněné v jednom datasetu
- `calendar_dates.txt` - 1.58 mil. kalendářních výjimek (státní svátky, prázdniny)
- `stop_times.txt.gz` - 6.9 mil. záznamů (52 MB komprimováno, 265 MB nekomprimováno)

## 🏙️ Seznam měst s MHD

### Krajská města
Praha (PID), Brno (IDSJMK), Ostrava (ODIS), Plzeň, Liberec, Olomouc, Ústí nad Labem, Hradec Králové, České Budějovice, Pardubice, Zlín, Havířov, Kladno, Karlovy Vary

### Další města (95)
Adamov, Aš, Benešov, Bílina, Blansko, Brandýs nad Labem, Břeclav, Bruntál, Bystřice nad Pernštejnem, České Těšín, Česká Lípa, Český Krumlov, Děčín, Domažlice, Duchcov, Dvůr Králové nad Labem, Frýdek-Místek, Havlíčkův Brod, Hodonín, Hořice, Hranice, Jablonec nad Nisou, Jáchymov, Jičín, Jihlava, Jindřichův Hradec, Karviná, Klášterec nad Ohří, Kolín, Kostelec nad Orlicí, Kralupy nad Vltavou, Kroměříž, Krnov, Kyjov, Litoměřice, Litomyšl, Louny, Lovosice, Mariánské Lázně, Mladá Boleslav, Milevsko, Mníšek pod Brdy, Most, Náchod, Nová Ves, Nové Město na Moravě, Opava, Orlová, Ostrov, Pelhřimov, Písek, Polička, Přelouč, Přerov, Příbram, Prostějov, Říčany, Rokycany, Roudnice nad Labem, Rychnov nad Kněžnou, Slaný, Sokolov, Špindlerův Mlýn, Štětí, Strakonice, Stříbro, Studenka, Šumperk, Tábor, Tachov, Teplice, Třebíč, Třinec, Trutnov, Turnov, Týniště nad Orlicí, Uherské Hradiště, Valašské Meziříčí, Varnsdorf, Velké Meziříčí, Vimperk, Vlašim, Vrchlabí, Vsetín, Vyškov, Znojmo, Žďár nad Sázavou, Zábřeh, Žatec

## 📋 Statistiky

### Celkový přehled

| Kategorie | Linky | Spoje | Stop times | Velikost |
|-----------|-------|-------|------------|----------|
| **MHD** | 4,588 | 301,953 | 5.9 mil. | 226 MB |
| **Regionální** | 2,147 | 82,732 | 1.0 mil. | 39 MB |
| **Celkem** | **6,735** | **384,685** | **6.9 mil.** | **265 MB** |

### Pokrytí

- **215 dopravních agentur** (městské dopravní podniky, České dráhy, soukromí dopravci)
- **61,052 unikátních zastávek** (po celé České republice)
- **1.58 mil. kalendářních výjimek** (svátky, prázdniny, víkendy)

### Typ dopravy

| Typ | GTFS route_type | Počet linek |
|-----|-----------------|-------------|
| Tramvaj | 0 | ~600 |
| Metro | 1 | 3 (Praha) |
| Vlak | 2 | ~1,900 |
| Autobus | 3 | ~4,200 |

## 🚀 Použití

### Poznámka o komprimovaných souborech

Velké `stop_times.txt` soubory jsou komprimované gzipem (`.txt.gz`) kvůli limitům GitHubu. GTFS specifikace oficiálně podporuje gzip komprimované soubory a většina nástrojů je automaticky dekomprimuje.

**Dekomprese (pokud potřebuješ nekomprimované soubory):**
```bash
gunzip data/mhd/stop_times.txt.gz
gunzip data/merged/stop_times.txt.gz
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
MHD_TRIP_0,MHD_ROUTE_0,WEEKDAY
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
WEEKDAY,1,1,1,1,1,1,1,20260208,20270208
```

## ⚠️ Omezení

### GPS souřadnice
Aktuální verze obsahuje zastávky s GPS souřadnicemi nastavenými na `0.0, 0.0`. Pro přesnou lokalizaci doporučujeme:
- Použití geocoding služeb (Google Maps API, Nominatim)
- Manuální doplnění souřadnic
- Propojení s oficiálními registr y zastávek

### Časové pokrytí
Dataset obsahuje jízdní řády platné pro:
- **Od:** 2026-02-08
- **Do:** 2027-02-08

### Rozsah dat
Dataset primárně pokrývá:
- ✅ Městskou hromadnou dopravu (MHD) - kompletní
- ⚠️ Regionální autobusy - vybrané linky
- ⚠️ Vlakové spoje - vybrané linky

Pro kompletní jízdní řády doporučujeme kombinaci s:
- [Oficiální GTFS data ČR](https://portal.cisjr.cz/)
- [PID OpenData](https://pid.cz/o-systemu/opendata/)
- [ODIS OpenData](https://www.odis.cz/)

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

Tento dataset vznikl agregací a konsolidací veřejně dostupných zdrojů jízdních řádů, včetně:

- **Oficiální GTFS data** z [portal.cisjr.cz](https://portal.cisjr.cz/) (Celostátní informační systém o jízdních řádech)
- **PID (Pražská integrovaná doprava)** - kompletní jízdní řády pro Prahu a Středočeský kraj
- **Regionální dopravní systémy** - ODIS, IDSJMK, IDOL a další
- **Městské dopravní podniky** - MHD pro města po celé ČR

Data byla deduplikována, normalizována a kategorizována pro snadnější použití v analytických a navigačních aplikacích.

## 📄 Licence

Dataset je poskytován pod licencí **CC BY 4.0** (Creative Commons Attribution 4.0 International).

Můžete data:
- ✅ Sdílet - kopírovat a distribuovat
- ✅ Upravovat - remixovat, transformovat, využívat pro další práci
- ✅ Komerčně využívat

Za podmínek:
- **Uvedení autora** - Musíte uvést odkaz na tento zdroj

## 🤝 Přispívání

Uvítáme příspěvky v oblasti:
- Doplnění GPS souřadnic zastávek
- Aktualizace jízdních řádů
- Rozšíření pokrytí o další města
- Opravy chyb v datech

## 📞 Kontakt

Pro otázky ohledně datasetu vytvořte issue na GitHubu.

## 🙏 Poděkování

Tento dataset vznikl jako součást projektu [stredniskoly.cz](https://stredniskoly.cz) pro analýzu dostupnosti středních škol veřejnou dopravou.

---

**Verze:** 2.0.0
**Poslední aktualizace:** 2026-02-08
**Formát:** GTFS (General Transit Feed Specification)
**Velikost datasetu:** ~530 MB (kompletní)
**Zdroje:** GTFS_CR, PID, vlastní agregace
