# Kvalita a pokrytí dat

## Přehled

Tento dokument popisuje kvalitu, úplnost a pokrytí GTFS datasetu pro Českou republiku.

## Pokrytí

### Městská hromadná doprava (MHD)

Dataset obsahuje **kompletní pokrytí** MHD pro 109 měst:

#### Krajská města (14)
✅ Všechna krajská města pokryta

- Praha - PID (Pražská integrovaná doprava)
- Brno - IDSJMK (Integrovaný dopravní systém Jihomoravského kraje)
- Ostrava - ODIS (Ostravský dopravní integrovaný systém)
- Plzeň
- Liberec
- Olomouc
- Ústí nad Labem
- Hradec Králové
- České Budějovice
- Pardubice
- Zlín
- Havířov
- Kladno
- Karlovy Vary

#### Malá a střední města (95)
✅ 95 dalších měst s MHD

Od Adamova po Zlín - viz kompletní seznam v README.md

### Regionální doprava

⚠️ **Částečné pokrytí**

Dataset obsahuje vybrané regionální linky:
- 5 vlakových linek (PID, ODIS, IDOL, IDSJMK)
- 2 meziměstské autobusové linky

**Poznámka:** Pro kompletní regionální jízdní řády doporučujeme použít oficiální GTFS data z [portal.cisjr.cz](https://portal.cisjr.cz/).

## Kvalita dat

### GPS souřadnice

**Status:** ⚠️ Nepřesné

Všechny zastávky mají GPS souřadnice nastavené na `0.0, 0.0`.

**Řešení:**
1. Použijte geocoding služby (Google Maps API, Nominatim)
2. Propojte s oficiálním registrem zastávek
3. Manuálně doplňte souřadnice pro kritické zastávky

**Příklad geocodingu:**
```python
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="transit_cz")

def geocode_stop(stop_name, city):
    query = f"{stop_name}, {city}, Czech Republic"
    location = geolocator.geocode(query)
    if location:
        return location.latitude, location.longitude
    return None, None

# Příklad
lat, lon = geocode_stop("Hlavní nádraží", "Pardubice")
print(f"Souřadnice: {lat}, {lon}")
```

### Názvy zastávek

**Status:** ✅ Dobré

Názvy zastávek jsou v češtině s diakritikou, ve formátu:
- "Hlavní nádraží"
- "Masarykovo náměstí"
- "Sídliště Východ"

**Kódování:** UTF-8

### Časové údaje

**Status:** ✅ Dobré

- Formát: `HH:MM:SS`
- Časová zóna: `Europe/Prague`
- Rozsah platnosti: 2026-02-08 až 2027-02-08

### Kalendář

**Status:** ⚠️ Zjednodušený

Aktuální verze obsahuje pouze jeden kalendář:
- `WEEKDAY` - platný všechny dny v týdnu

**Chybí:**
- Rozlišení pracovní dny / víkendy
- Svátky a školní prázdniny
- Letní/zimní jízdní řády

**Doporučení:** Pro produkční použití doplňte kalendářní výjimky pomocí `calendar_dates.txt`.

### Přepravci

**Status:** ⚠️ Syntetické údaje

Dataset obsahuje 3 syntetické přepravce:
- "Městská hromadná doprava"
- "České dráhy"
- "Meziměstské autobusy"

**Poznámka:** Reálná data by měla obsahovat skutečné dopravní společnosti (Dopravní podnik města Brna, ČSAD, atd.)

## Statistiky kvality

| Metr ika | Hodnota | Status |
|----------|---------|--------|
| Celkem zastávek | 18,862 | ✅ |
| Zastávky s GPS | 0 (0%) | ⚠️ |
| Celkem linek | 116 | ✅ |
| Celkem spojů | 15,121 | ✅ |
| Kalendářní výjimky | 0 | ⚠️ |
| Transfers | 0 | ⚠️ |

## Validace

### GTFS Validator

```bash
# Instalace
npm install -g gtfs-validator

# Validace
gtfs-validator data/mhd/

# Očekávané varování:
# - Missing GPS coordinates for stops
# - No calendar_dates.txt
# - No transfers.txt
```

### Typické chyby

#### Chybějící GPS souřadnice
```
WARNING: stop_lat and stop_lon are 0.0 for stop_id MHD_STOP_0
```
**Řešení:** Geocoding (viz výše)

#### Chybějící calendar_dates.txt
```
INFO: calendar_dates.txt not found
```
**Řešení:** Vytvo řte calendar_dates.txt se svátky:
```
service_id,date,exception_type
WEEKDAY,20261225,2
WEEKDAY,20261226,2
WEEKDAY,20270101,2
```

#### Chybějící transfers.txt
```
INFO: transfers.txt not found
```
**Řešení:** Přidejte přestupní body:
```
from_stop_id,to_stop_id,transfer_type,min_transfer_time
MHD_STOP_0,MHD_STOP_1,2,180
```

## Srovnání s jinými datasety

### Oficiální GTFS ČR (portal.cisjr.cz)

| Metrika | Tento dataset | GTFS_CR | Pokrytí |
|---------|---------------|---------|---------|
| Agencies | 3 | 211 | 1.4% |
| Zastávky | 18,862 | 86,897 | 21.7% |
| Linky | 116 | 5,767 | 2.0% |
| Spoje | 15,121 | 295,855 | 5.1% |

**Závěr:** Tento dataset pokrývá primárně MHD a je vhodný jako doplněk oficiálních dat.

## Doporučení pro použití

### ✅ Vhodné pro:
- Analýzu dostupnosti v rámci měst
- Vizualizaci MHD sítí
- Prototypování dopravních aplikací
- Offline použití (bez potřeby velkých datasetů)
- Výzkum urban mobility

### ⚠️ Nevhodné pro:
- Produkční navigační aplikace (chybí GPS)
- Přesné výpočty dojezdových časů
- Regionální/dálkové spoje (neúplné pokrytí)
- Real-time informace (statická data)

## Plán zlepšení

### Fáze 1: GPS souřadnice
- [ ] Geocoding všech zastávek
- [ ] Validace správnosti souřadnic
- [ ] Doplnění stop_code z oficiálních registrů

### Fáze 2: Kalendář
- [ ] Rozdělení na pracovní dny/víkendy
- [ ] Doplnění státních svátků
- [ ] Školní prázdniny
- [ ] Letní/zimní jízdní řády

### Fáze 3: Rozšíření dat
- [ ] Kompletní regionální autobusy
- [ ] Všechny vlakové spoje
- [ ] Transfers mezi linkami
- [ ] Fare zones a ceny jízdenek

### Fáze 4: Realtime
- [ ] GTFS Realtime feed
- [ ] Zpoždění v reálném čase
- [ ] Výluky a objížďky
- [ ] Obsazenost vozidel

## Kontakt

Pro hlášení chyb v datech nebo návrhy vylepšení vytvořte issue na GitHubu.

---

**Poslední aktualizace:** 2026-02-08
**Verze datasetu:** 1.0.0
