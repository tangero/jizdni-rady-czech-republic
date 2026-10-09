# Kvalita dat

Stav k verzi **2.2.0** (data CIS JŘ publikovaná 9. 10. 2026).

## Kontrola konzistence

Každé sestavení se ověřuje skriptem `scripts/validate_gtfs.py`, který kontroluje:

- každý spoj odkazuje na existující linku a má definovanou platnost (`calendar.txt` / `calendar_dates.txt`)
- každá linka odkazuje na existujícího dopravce
- každý záznam `stop_times` odkazuje na existující spoj a zastávku
- každý spoj má alespoň dvě zastávky

Výsledek pro verzi 2.2.0:

| Dataset | Dopravci | Zastávky | Linky | Spoje | Stop times | Výsledek |
|---------|----------|----------|-------|-------|------------|----------|
| mhd | 241 | 36,937 | 4,196 | 244,800 | 4,627,950 | ✅ OK |
| regional | 241 | 36,937 | 1,944 | 44,557 | 594,725 | ✅ OK |
| merged | 241 | 36,937 | 6,140 | 289,357 | 5,222,675 | ✅ OK |

Předchozí verze touto kontrolou neprocházely. Ve verzích 2.0.0 i 2.1.0 chyběl obsah `calendar.txt`, takže většina spojů neměla definovanou platnost. Ve verzi 2.1.0 navíc `stop_times.txt.gz` pocházel z jiného sestavení než `trips.txt` a `stops.txt`.

## Zastávky

- Souřadnice pocházejí z CIS JŘ, bez GPS (`0.0, 0.0`) je 353 zastávek (~1 %).
- Zastávky jsou deduplikované podle názvu ve formátu „Obec, zastávka“. Jednotlivá nástupiště jsou sloučena do jednoho bodu se souřadnicemi prvního nástupiště.
- Ve výstupu jsou jen zastávky, na které odkazuje alespoň jeden spoj.

## Kalendář

- `calendar.txt` a `calendar_dates.txt` jsou převzaty ze zdroje beze změny (jen s přemapovanými ID).
- Spoje, které od data sestavení už nejedou, jsou vyřazeny (`--from-date`, default dnešek).
- Pokrytí dopředu je omezené tím, co dopravci publikují. PID zhruba 2 týdny, ostatní typicky do konce platnosti ročního jízdního řádu (12. 12. 2026).

## Dělení MHD / regionální

Dělení je heuristické (`_is_mhd_route` v `scripts/integrate_all_data_fast.py`):

- tramvaj, metro, trolejbus → MHD
- vlak → regionální
- autobus s číslem linky do tří číslic (případně `N` + číslo) → MHD, jinak regionální

CIS JŘ neposkytuje spolehlivý příznak (sloupec `is_regional` je všude `0`), proto regionální linky integrovaných systémů s trojmístným číslem (PID 3xx–7xx, ODIS 3xx a další) spadají do `mhd/`. Pro routing používejte `merged/`.

## Doporučená externí validace

```bash
java -jar gtfs-validator-cli.jar -i data/merged -o validation-report
```

[MobilityData GTFS Validator](https://github.com/MobilityData/gtfs-validator) bude hlásit chybějící `feed_info.txt` a volitelné sloupce, které dataset záměrně neobsahuje.
