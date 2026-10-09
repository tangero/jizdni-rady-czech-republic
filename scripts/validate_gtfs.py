#!/usr/bin/env python3
"""
Kontrola konzistence výstupních GTFS datasetů (data/mhd, data/regional, data/merged).

Ověřuje:
    - každý trip odkazuje na existující route a service (calendar / calendar_dates)
    - každá route odkazuje na existující agency
    - každý záznam stop_times odkazuje na existující trip a stop
    - každý trip má alespoň dva záznamy ve stop_times
    - časové pokrytí kalendáře (nejdřívější a nejzazší den provozu)

Použití:
    python scripts/validate_gtfs.py                 # všechny datasety
    python scripts/validate_gtfs.py data/merged     # konkrétní adresář

Návratový kód 1, pokud se najde chyba.
"""

import csv
import gzip
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator, List, Set

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DIRS = [PROJECT_DIR / 'data' / name for name in ('mhd', 'regional', 'merged')]


def _rows(path: Path) -> Iterator[dict]:
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8-sig', newline='') as f:
        yield from csv.DictReader(f)


def _ids(path: Path, column: str) -> Set[str]:
    return {row[column] for row in _rows(path)} if path.exists() else set()


def validate(dataset: Path) -> List[str]:
    errors: List[str] = []
    print(f"\n== {dataset.relative_to(PROJECT_DIR) if dataset.is_relative_to(PROJECT_DIR) else dataset}")

    stop_times = dataset / 'stop_times.txt.gz'
    if not stop_times.exists():
        stop_times = dataset / 'stop_times.txt'
    for required in ('agency.txt', 'stops.txt', 'routes.txt', 'trips.txt'):
        if not (dataset / required).exists():
            errors.append(f"chybí {required}")
    if not stop_times.exists():
        errors.append("chybí stop_times.txt(.gz)")
    if errors:
        return errors

    agencies = _ids(dataset / 'agency.txt', 'agency_id')
    stops = _ids(dataset / 'stops.txt', 'stop_id')
    routes = {r['route_id']: r['agency_id'] for r in _rows(dataset / 'routes.txt')}
    services = _ids(dataset / 'calendar.txt', 'service_id') | _ids(dataset / 'calendar_dates.txt', 'service_id')

    bad_agency = sum(1 for a in routes.values() if a not in agencies)
    if bad_agency:
        errors.append(f"{bad_agency} linek odkazuje na neexistujícího dopravce")

    trips: Set[str] = set()
    bad_route = bad_service = 0
    for t in _rows(dataset / 'trips.txt'):
        trips.add(t['trip_id'])
        bad_route += t['route_id'] not in routes
        bad_service += t['service_id'] not in services
    if bad_route:
        errors.append(f"{bad_route} spojů odkazuje na neexistující linku")
    if bad_service:
        errors.append(f"{bad_service} spojů nemá definovanou platnost (service_id chybí v calendar*)")

    st_per_trip: Counter = Counter()
    bad_trip = bad_stop = total = 0
    for st in _rows(stop_times):
        total += 1
        if st['trip_id'] not in trips:
            bad_trip += 1
        else:
            st_per_trip[st['trip_id']] += 1
        bad_stop += st['stop_id'] not in stops
    if bad_trip:
        errors.append(f"{bad_trip} stop_times odkazuje na neexistující spoj")
    if bad_stop:
        errors.append(f"{bad_stop} stop_times odkazuje na neexistující zastávku")
    short_trips = sum(1 for t in trips if st_per_trip[t] < 2)
    if short_trips:
        errors.append(f"{short_trips} spojů má méně než 2 zastávky")

    # Časové pokrytí
    days: List[str] = []
    if (dataset / 'calendar.txt').exists():
        for c in _rows(dataset / 'calendar.txt'):
            days += [c['start_date'], c['end_date']]
    if (dataset / 'calendar_dates.txt').exists():
        days += [c['date'] for c in _rows(dataset / 'calendar_dates.txt') if c['exception_type'] == '1']

    no_coords = sum(1 for s in _rows(dataset / 'stops.txt') if s['stop_lat'] in ('', '0.0', '0'))

    print(f"  dopravci {len(agencies):,} | zastávky {len(stops):,} (bez GPS {no_coords:,}) | "
          f"linky {len(routes):,} | spoje {len(trips):,} | stop_times {total:,}")
    if days:
        print(f"  kalendář: {min(days)} – {max(days)}")
    for e in errors:
        print(f"  CHYBA: {e}")
    if not errors:
        print("  OK")
    return errors


def main():
    dirs = [Path(p).resolve() for p in sys.argv[1:]] or DEFAULT_DIRS
    failed = [d for d in dirs if validate(d)]
    if failed:
        print(f"\nNalezeny chyby v {len(failed)} datasetech")
        sys.exit(1)
    print("\nVšechny datasety jsou konzistentní")


if __name__ == '__main__':
    main()
