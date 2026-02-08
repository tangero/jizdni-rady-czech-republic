# Jízdní řády České republiky - GTFS Dataset

Agregovaná a konsolidovaná data veřejné dopravy v České republice ve standardním GTFS formátu.

## 📊 Přehled datasetu

Tento dataset obsahuje kompletní informace o jízdních řádech městské hromadné dopravy (MHD) a vybraných regionálních spojích v České republice.

### Pokrytí

- **109 měst** s MHD
- **18,862 zastávek**
- **116 dopravních linek**
- **15,121 denních spojů**

## 🗂️ Struktura dat

### data/mhd/
Městská hromadná doprava (MHD) pro 109 měst po celé České republice.

**Standardní GTFS soubory:**
- `agency.txt` - Dopravní agentury
- `stops.txt` - Zastávky a stanice
- `routes.txt` - Linky a trasy
- `trips.txt` - Jednotlivé spoje
- `stop_times.txt` - Časy příjezdů a odjezdů
- `calendar.txt` - Kalendář platnosti

### data/regional/
Vybrané regionální a dálkové spoje (připravováno).

### data/merged/
Sloučený dataset pro použití v aplikacích (připravováno).

## 🏙️ Seznam měst s MHD

### Krajská města
Praha (PID), Brno (IDSJMK), Ostrava (ODIS), Plzeň, Liberec, Olomouc, Ústí nad Labem, Hradec Králové, České Budějovice, Pardubice, Zlín, Havířov, Kladno, Karlovy Vary

### Další města (95)
Adamov, Aš, Benešov, Bílina, Blansko, Brandýs nad Labem, Břeclav, Bruntál, Bystřice nad Pernštejnem, České Těšín, Česká Lípa, Český Krumlov, Děčín, Domažlice, Duchcov, Dvůr Králové nad Labem, Frýdek-Místek, Havlíčkův Brod, Hodonín, Hořice, Hranice, Jablonec nad Nisou, Jáchymov, Jičín, Jihlava, Jindřichův Hradec, Karviná, Klášterec nad Ohří, Kolín, Kostelec nad Orlicí, Kralupy nad Vltavou, Kroměříž, Krnov, Kyjov, Litoměřice, Litomyšl, Louny, Lovosice, Mariánské Lázně, Mladá Boleslav, Milevsko, Mníšek pod Brdy, Most, Náchod, Nová Ves, Nové Město na Moravě, Opava, Orlová, Ostrov, Pelhřimov, Písek, Polička, Přelouč, Přerov, Příbram, Prostějov, Říčany, Rokycany, Roudnice nad Labem, Rychnov nad Kněžnou, Slaný, Sokolov, Špindlerův Mlýn, Štětí, Strakonice, Stříbro, Studenka, Šumperk, Tábor, Tachov, Teplice, Třebíč, Třinec, Trutnov, Turnov, Týniště nad Orlicí, Uherské Hradiště, Valašské Meziříčí, Varnsdorf, Velké Meziříčí, Vimperk, Vlašim, Vrchlabí, Vsetín, Vyškov, Znojmo, Žďár nad Sázavou, Zábřeh, Žatec

## 📋 Statistiky

### Celkový přehled

| Kategorie | Města/Linky | Zastávky | Spoje |
|-----------|-------------|----------|-------|
| MHD | 109 | 11,231 | 14,566 |
| Vlaky | 5 | 4,507 | 410 |
| Autobusy | 2 | 3,124 | 145 |
| **Celkem** | **116** | **18,862** | **15,121** |

### Top 10 měst podle počtu zastávek

1. **Hradec Králové** - 4,687 zastávek
2. **Praha (PID vlaky)** - 3,838 zastávek
3. **Meziměstské autobusy** - 3,000 zastávek
4. **Jindřichův Hradec** - 863 zastávek
5. **Karlovy Vary** - 557 zastávek
6. **Slaný** - 552 zastávek
7. **Vyškov** - 470 zastávek
8. **Kroměříž** - 390 zastávek
9. **Jihlava** - 253 zastávek
10. **IDOL vlaky** - 204 zastávek

## 🚀 Použití

### Rychlý start

```python
import csv

# Načtení zastávek
with open('data/mhd/stops.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    stops = list(reader)
    print(f"Nalezeno {len(stops)} zastávek")

# Načtení linek
with open('data/mhd/routes.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    routes = list(reader)
    print(f"Nalezeno {len(routes)} linek")
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

Všechna data v tomto datasetu vznikla agregací veřejně dostupných zdrojů včetně:
- Oficiálních jízdních řádů dopravních společností
- Otevřených dat z portálů veřejné správy
- Integrovaných dopravních systémů (PID, ODIS, IDSJMK)
- Městských dopravních podniků

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

**Verze:** 1.0.0
**Poslední aktualizace:** 2026-02-08
**Formát:** GTFS (General Transit Feed Specification)
