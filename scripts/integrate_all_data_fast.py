#!/usr/bin/env python3
"""
Rychlá integrace GTFS zdrojů do datasetů data/mhd, data/regional a data/merged.

Bez externích závislostí, stop_times se zpracovávají průběžně (streaming)
a zapisují rovnou jako stop_times.txt.gz.

Zdroje (výchozí cesty, stažené přes scripts/download_sources.py):
    GTFS_CR  data/sources/GTFS_CR   - CIS JŘ, páteřní zdroj (obsahuje i PID a MHD)
    PID      data/sources/PID       - volitelně (--with-pid); GTFS_CR už PID obsahuje,
                                      takže zapnutí vede k duplicitním spojům
    TT       data/tt_source/ALL     - volitelně (--with-tt); heuristicky dekódovaný
                                      KOMPLET.ZIP bez GPS a s obecným kalendářem

Použití:
    python scripts/integrate_all_data_fast.py
    python scripts/integrate_all_data_fast.py --with-tt --from-date 20261201
"""

import argparse
import csv
import gzip
import io
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

PROJECT_DIR = Path(__file__).resolve().parent.parent

AGENCY_FIELDS = ['agency_id', 'agency_name', 'agency_url', 'agency_timezone', 'agency_lang']
STOP_FIELDS = ['stop_id', 'stop_name', 'stop_lat', 'stop_lon']
ROUTE_FIELDS = ['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type']
TRIP_FIELDS = ['trip_id', 'route_id', 'service_id']
CALENDAR_FIELDS = ['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                   'saturday', 'sunday', 'start_date', 'end_date']
CALENDAR_DATE_FIELDS = ['service_id', 'date', 'exception_type']
STOP_TIME_FIELDS = ['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time']

WEEKDAYS = CALENDAR_FIELDS[1:8]
DATASETS = ('mhd', 'regional', 'merged')


def _open_csv(file_path: Path):
    """Otevře GTFS CSV (toleruje BOM)."""
    return open(file_path, 'r', encoding='utf-8-sig', newline='')


def _has_coords(lat: str, lon: str) -> bool:
    try:
        return float(lat) != 0.0 and float(lon) != 0.0
    except (TypeError, ValueError):
        return False


class GTFSIntegratorFast:
    def __init__(self, from_date: str):
        self.from_date = from_date

        self.next_agency_id = 1
        self.next_stop_id = 1
        self.next_route_id = 1
        self.next_trip_id = 1
        self.next_service_id = 1

        # Mapování původních ID na nová (per zdroj)
        self.agency_map: Dict[str, Dict[str, str]] = {}
        self.stop_map: Dict[str, Dict[str, str]] = {}
        self.route_map: Dict[str, Dict[str, str]] = {}
        self.trip_map: Dict[str, Dict[str, str]] = {}
        self.service_map: Dict[str, Dict[str, str]] = {}

        # Deduplikace zastávek podle názvu: název -> index v self.stops
        self.stop_names: Dict[str, int] = {}

        self.agencies: List[Dict] = []
        self.stops: List[Dict] = []
        self.routes_mhd: List[Dict] = []
        self.routes_regional: List[Dict] = []
        self.trips_mhd: List[Dict] = []
        self.trips_regional: List[Dict] = []
        self.calendar: List[Dict] = []
        self.calendar_dates: List[Dict] = []

        self.mhd_route_ids: Set[str] = set()
        self.mhd_trip_ids: Set[str] = set()
        self.active_services: Set[str] = set()
        self.skipped_trips = 0

    def load_source(self, source_dir: Path, source_name: str):
        """Načte jeden GTFS zdroj a remapuje ID."""
        print(f"\nNačítám: {source_name} ({source_dir})")

        for mapping in (self.agency_map, self.stop_map, self.route_map, self.trip_map, self.service_map):
            mapping[source_name] = {}

        self._load_agencies(source_dir, source_name)
        self._load_stops(source_dir, source_name)
        self._load_routes(source_dir, source_name)
        self._load_calendar(source_dir, source_name)
        self._load_calendar_dates(source_dir, source_name)
        self._load_trips(source_dir, source_name)
        # stop_times se nenačítají do paměti, zpracují se v process_stop_times()

    def _load_agencies(self, source_dir: Path, source_name: str):
        file_path = source_dir / 'agency.txt'
        if not file_path.exists():
            return

        with _open_csv(file_path) as f:
            for row in csv.DictReader(f):
                new_id = f'AG_{self.next_agency_id}'
                self.next_agency_id += 1
                self.agency_map[source_name][row.get('agency_id', '')] = new_id

                self.agencies.append({
                    'agency_id': new_id,
                    'agency_name': row['agency_name'],
                    'agency_url': row.get('agency_url', ''),
                    'agency_timezone': row.get('agency_timezone') or 'Europe/Prague',
                    'agency_lang': row.get('agency_lang') or 'cs',
                })

    def _load_stops(self, source_dir: Path, source_name: str):
        """Načte zastávky s deduplikací podle názvu."""
        file_path = source_dir / 'stops.txt'
        if not file_path.exists():
            return

        new_stops = 0
        filled_coords = 0

        with _open_csv(file_path) as f:
            for row in csv.DictReader(f):
                stop_name = row['stop_name']
                lat, lon = row.get('stop_lat', ''), row.get('stop_lon', '')

                idx = self.stop_names.get(stop_name)
                if idx is None:
                    idx = len(self.stops)
                    self.stop_names[stop_name] = idx
                    self.stops.append({
                        'stop_id': f'ST_{self.next_stop_id}',
                        'stop_name': stop_name,
                        'stop_lat': lat if _has_coords(lat, lon) else '0.0',
                        'stop_lon': lon if _has_coords(lat, lon) else '0.0',
                    })
                    self.next_stop_id += 1
                    new_stops += 1
                else:
                    # Doplň souřadnice, pokud je dřívější zdroj neměl
                    stop = self.stops[idx]
                    if not _has_coords(stop['stop_lat'], stop['stop_lon']) and _has_coords(lat, lon):
                        stop['stop_lat'], stop['stop_lon'] = lat, lon
                        filled_coords += 1

                self.stop_map[source_name][row['stop_id']] = self.stops[idx]['stop_id']

        print(f"  Zastávky: +{new_stops} nových, doplněno souřadnic: {filled_coords}")

    def _load_routes(self, source_dir: Path, source_name: str):
        """Načte linky s kategorizací MHD / regionální."""
        file_path = source_dir / 'routes.txt'
        if not file_path.exists():
            return

        mhd_count = 0
        regional_count = 0

        with _open_csv(file_path) as f:
            for row in csv.DictReader(f):
                new_id = f'RT_{self.next_route_id}'
                self.next_route_id += 1
                self.route_map[source_name][row['route_id']] = new_id

                route_data = {
                    'route_id': new_id,
                    'agency_id': self.agency_map[source_name].get(row.get('agency_id', ''), ''),
                    'route_short_name': row.get('route_short_name', ''),
                    'route_long_name': row.get('route_long_name', ''),
                    'route_type': row.get('route_type') or '3',
                }

                if self._is_mhd_route(route_data['route_short_name'], route_data['route_type']):
                    self.routes_mhd.append(route_data)
                    self.mhd_route_ids.add(new_id)
                    mhd_count += 1
                else:
                    self.routes_regional.append(route_data)
                    regional_count += 1

        print(f"  Linky: +{mhd_count} MHD, +{regional_count} regionální")

    def _map_service(self, source_name: str, old_id: str) -> str:
        """Vrátí nové service_id (každé původní ID se mapuje jen jednou)."""
        mapping = self.service_map[source_name]
        if old_id not in mapping:
            mapping[old_id] = f'SV_{self.next_service_id}'
            self.next_service_id += 1
        return mapping[old_id]

    def _load_calendar(self, source_dir: Path, source_name: str):
        file_path = source_dir / 'calendar.txt'
        if not file_path.exists():
            return

        count = 0
        with _open_csv(file_path) as f:
            for row in csv.DictReader(f):
                old_id = row['service_id']
                if old_id in self.service_map[source_name]:
                    continue  # duplicitní řádek ve zdroji
                new_id = self._map_service(source_name, old_id)

                entry = {field: row[field] for field in CALENDAR_FIELDS}
                entry['service_id'] = new_id
                self.calendar.append(entry)
                count += 1

                if entry['end_date'] >= self.from_date and any(entry[d] == '1' for d in WEEKDAYS):
                    self.active_services.add(new_id)

        print(f"  Calendar: +{count}")

    def _load_calendar_dates(self, source_dir: Path, source_name: str):
        file_path = source_dir / 'calendar_dates.txt'
        if not file_path.exists():
            return

        count = 0
        with _open_csv(file_path) as f:
            for row in csv.DictReader(f):
                new_id = self._map_service(source_name, row['service_id'])
                exception_type = row.get('exception_type') or '1'
                self.calendar_dates.append({
                    'service_id': new_id,
                    'date': row['date'],
                    'exception_type': exception_type,
                })
                if exception_type == '1' and row['date'] >= self.from_date:
                    self.active_services.add(new_id)
                count += 1

        print(f"  Calendar dates: +{count}")

    def _load_trips(self, source_dir: Path, source_name: str):
        """Načte spoje; vynechá spoje bez linky nebo bez platnosti od from_date."""
        file_path = source_dir / 'trips.txt'
        if not file_path.exists():
            return

        mhd_count = 0
        regional_count = 0
        skipped = 0

        with _open_csv(file_path) as f:
            for row in csv.DictReader(f):
                route_new = self.route_map[source_name].get(row.get('route_id', ''))
                service_new = self.service_map[source_name].get(row.get('service_id', ''))

                if not route_new or service_new not in self.active_services:
                    skipped += 1
                    continue

                new_id = f'TR_{self.next_trip_id}'
                self.next_trip_id += 1
                self.trip_map[source_name][row['trip_id']] = new_id

                trip_data = {'trip_id': new_id, 'route_id': route_new, 'service_id': service_new}

                if route_new in self.mhd_route_ids:
                    self.trips_mhd.append(trip_data)
                    self.mhd_trip_ids.add(new_id)
                    mhd_count += 1
                else:
                    self.trips_regional.append(trip_data)
                    regional_count += 1

        self.skipped_trips += skipped
        print(f"  Spoje: +{mhd_count} MHD, +{regional_count} regionální, vynecháno {skipped} (neplatné od {self.from_date})")

    @staticmethod
    def _is_mhd_route(route_name: str, route_type: str) -> bool:
        """Určí, jestli je linka MHD nebo regionální."""
        # Tramvaje, metro, trolejbusy - vždy MHD
        if route_type in ('0', '1', '11'):
            return True

        # Vlaky - regionální
        if route_type == '2':
            return False

        # Autobusy - podle čísla linky
        if route_type == '3':
            if route_name.isdigit() and len(route_name) <= 3:
                return True
            if route_name.startswith('N') and len(route_name) <= 3:
                return True

        return False

    def prune(self):
        """Odstraní linky, kalendáře a zastávky, na které nic neodkazuje."""
        used_routes = {t['route_id'] for t in self.trips_mhd} | {t['route_id'] for t in self.trips_regional}
        used_services = {t['service_id'] for t in self.trips_mhd} | {t['service_id'] for t in self.trips_regional}

        self.routes_mhd = [r for r in self.routes_mhd if r['route_id'] in used_routes]
        self.routes_regional = [r for r in self.routes_regional if r['route_id'] in used_routes]
        self.calendar = [c for c in self.calendar if c['service_id'] in used_services]
        self.calendar_dates = [c for c in self.calendar_dates if c['service_id'] in used_services]

        used_agencies = {r['agency_id'] for r in self.routes_mhd + self.routes_regional}
        self.agencies = [a for a in self.agencies if a['agency_id'] in used_agencies]

    def prune_stops(self, used_stops: Set[str]):
        self.stops = [s for s in self.stops if s['stop_id'] in used_stops]

    def process_stop_times(self, sources: List[tuple], output_dir: Path) -> Set[str]:
        """Zpracuje stop_times všech zdrojů průběžně a zapíše .txt.gz. Vrací použité zastávky."""
        used_stops: Set[str] = set()
        writers = {}
        handles = []

        for name in DATASETS:
            path = output_dir / name / 'stop_times.txt.gz'
            raw = open(path, 'wb')
            # mtime=0 a prázdné jméno -> deterministický výstup (menší git diffy)
            gz = gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=6, mtime=0, filename='')
            text = io.TextIOWrapper(gz, encoding='utf-8', newline='')
            handles.append((text, gz, raw))
            writer = csv.writer(text)
            writer.writerow(STOP_TIME_FIELDS)
            writers[name] = writer

        try:
            for source_name, source_dir in sources:
                file_path = source_dir / 'stop_times.txt'
                if not file_path.exists():
                    continue

                print(f"  Stop times ({source_name}): zpracovávám", end='', flush=True)
                trip_map = self.trip_map[source_name]
                stop_map = self.stop_map[source_name]
                mhd_count = regional_count = processed = 0

                with _open_csv(file_path) as f_in:
                    for row in csv.DictReader(f_in):
                        trip_new = trip_map.get(row['trip_id'])
                        if not trip_new:
                            continue
                        stop_new = stop_map.get(row['stop_id'])
                        if not stop_new:
                            continue

                        record = [
                            trip_new,
                            stop_new,
                            row.get('stop_sequence') or '0',
                            row.get('arrival_time') or '',
                            row.get('departure_time') or '',
                        ]
                        used_stops.add(stop_new)

                        if trip_new in self.mhd_trip_ids:
                            writers['mhd'].writerow(record)
                            mhd_count += 1
                        else:
                            writers['regional'].writerow(record)
                            regional_count += 1
                        writers['merged'].writerow(record)

                        processed += 1
                        if processed % 1_000_000 == 0:
                            print('.', end='', flush=True)

                print(f" +{mhd_count:,} MHD, +{regional_count:,} regionální")
        finally:
            for text, gz, raw in handles:
                text.close()
                raw.close()

        return used_stops

    def export_metadata(self, output_dir: Path):
        """Exportuje vše kromě stop_times."""
        print("\n" + "=" * 80)
        print("EXPORT METADAT")
        print("=" * 80)

        dirs = {name: output_dir / name for name in DATASETS}
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)
            # Starý nekomprimovaný stop_times by byl zastaralý a matoucí
            (d / 'stop_times.txt').unlink(missing_ok=True)

        routes = {
            'mhd': self.routes_mhd,
            'regional': self.routes_regional,
            'merged': self.routes_mhd + self.routes_regional,
        }
        trips = {
            'mhd': self.trips_mhd,
            'regional': self.trips_regional,
            'merged': self.trips_mhd + self.trips_regional,
        }

        for name, d in dirs.items():
            used_services = {t['service_id'] for t in trips[name]}
            calendar = [c for c in self.calendar if c['service_id'] in used_services]
            calendar_dates = [c for c in self.calendar_dates if c['service_id'] in used_services]

            self._write_csv(d / 'agency.txt', self.agencies, AGENCY_FIELDS)
            self._write_csv(d / 'stops.txt', self.stops, STOP_FIELDS)
            self._write_csv(d / 'routes.txt', routes[name], ROUTE_FIELDS)
            self._write_csv(d / 'trips.txt', trips[name], TRIP_FIELDS)
            self._write_csv(d / 'calendar.txt', calendar, CALENDAR_FIELDS)
            self._write_csv(d / 'calendar_dates.txt', calendar_dates, CALENDAR_DATE_FIELDS)

            print(f"  {name}: {len(routes[name]):,} linek, {len(trips[name]):,} spojů, "
                  f"{len(calendar):,} kalendářů, {len(calendar_dates):,} výjimek")
        print(f"  společné: {len(self.agencies):,} dopravců, {len(self.stops):,} zastávek")

    @staticmethod
    def _write_csv(file_path: Path, data: List[Dict], fieldnames: List[str]):
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integrace GTFS zdrojů do data/mhd|regional|merged")
    parser.add_argument('--gtfs-cr', type=Path, default=PROJECT_DIR / 'data' / 'sources' / 'GTFS_CR',
                        help='Adresář s rozbaleným GTFS CIS JŘ')
    parser.add_argument('--pid', type=Path, default=PROJECT_DIR / 'data' / 'sources' / 'PID',
                        help='Adresář s rozbaleným PID GTFS')
    parser.add_argument('--tt', type=Path, default=PROJECT_DIR / 'data' / 'tt_source' / 'ALL',
                        help='Adresář s GTFS z TT konverze')
    parser.add_argument('--with-pid', action='store_true',
                        help='Přidat PID zvlášť (pozor: GTFS_CR už PID obsahuje -> duplicity)')
    parser.add_argument('--with-tt', action='store_true',
                        help='Přidat data z TT konverze (KOMPLET.ZIP)')
    parser.add_argument('--from-date', default=date.today().strftime('%Y%m%d'),
                        help='Vynechat spoje, které od tohoto data (YYYYMMDD) už nejedou (default: dnes)')
    parser.add_argument('--output-dir', type=Path, default=PROJECT_DIR / 'data')
    args = parser.parse_args(argv)
    datetime.strptime(args.from_date, '%Y%m%d')  # validace formátu
    return args


def main(argv: Optional[List[str]] = None):
    args = parse_args(argv)

    # Pořadí je důležité: první zdroj vyhrává při deduplikaci zastávek podle názvu
    sources = [('GTFS_CR', args.gtfs_cr)]
    if args.with_pid:
        sources.append(('PID', args.pid))
    if args.with_tt:
        sources.append(('TT-converted', args.tt))

    missing = [f"{name}: {path}" for name, path in sources if not (path / 'trips.txt').exists()]
    if missing:
        raise SystemExit("Chybí zdrojová data (spusť scripts/download_sources.py):\n  " + "\n  ".join(missing))

    print("=" * 80)
    print(f"INTEGRACE GTFS DAT (spoje platné od {args.from_date})")
    print("=" * 80)

    integrator = GTFSIntegratorFast(args.from_date)
    for name, path in sources:
        integrator.load_source(path, name)

    integrator.prune()

    print("\n" + "=" * 80)
    print("ZPRACOVÁNÍ STOP_TIMES")
    print("=" * 80)
    for name in DATASETS:
        (args.output_dir / name).mkdir(parents=True, exist_ok=True)
    used_stops = integrator.process_stop_times(sources, args.output_dir)
    integrator.prune_stops(used_stops)

    integrator.export_metadata(args.output_dir)

    print("\n" + "=" * 80)
    print("HOTOVO")
    print("=" * 80)
    print("Ověření konzistence: python scripts/validate_gtfs.py")


if __name__ == '__main__':
    main()
