#!/usr/bin/env python3
"""
Rychlá integrace všech GTFS dat bez pandas závislosti.
Používá buffered I/O a batch processing pro velké soubory.
"""

import csv
from pathlib import Path
from typing import Dict, Set, List
import sys

class GTFSIntegratorFast:
    def __init__(self):
        self.next_agency_id = 1
        self.next_stop_id = 1
        self.next_route_id = 1
        self.next_trip_id = 1
        self.next_service_id = 1

        # Mapování původních ID na nová
        self.agency_map: Dict[str, Dict[str, str]] = {}
        self.stop_map: Dict[str, Dict[str, str]] = {}
        self.route_map: Dict[str, Dict[str, str]] = {}
        self.trip_map: Dict[str, Dict[str, str]] = {}
        self.service_map: Dict[str, Dict[str, str]] = {}

        # Deduplikace zastávek podle názvu
        self.stop_names: Dict[str, str] = {}

        # Výsledné soubory - budeme psát průběžně
        self.agencies = []
        self.stops = []
        self.routes_mhd = []
        self.routes_regional = []
        self.trips_mhd = []
        self.trips_regional = []
        self.calendar_dates = []

        # MHD trip IDs pro rychlé vyhledávání
        self.mhd_trip_ids: Set[str] = set()

    def load_source(self, source_dir: Path, source_name: str):
        """Načte jeden GTFS zdroj a remapuje ID."""
        print(f"\nNačítám: {source_name}")

        self.agency_map[source_name] = {}
        self.stop_map[source_name] = {}
        self.route_map[source_name] = {}
        self.trip_map[source_name] = {}
        self.service_map[source_name] = {}

        # 1. Agency
        self._load_agencies(source_dir, source_name)

        # 2. Stops
        self._load_stops(source_dir, source_name)

        # 3. Routes
        self._load_routes(source_dir, source_name)

        # 4. Calendar
        self._load_calendar(source_dir, source_name)

        # 5. Calendar dates
        self._load_calendar_dates(source_dir, source_name)

        # 6. Trips
        self._load_trips(source_dir, source_name)

        # 7. Stop times - NEBUDEME načítat do paměti, pouze zpracujeme později
        # Toto je klíčová optimalizace

    def _load_agencies(self, source_dir: Path, source_name: str):
        """Načte agencies."""
        file_path = source_dir / 'agency.txt'
        if not file_path.exists():
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['agency_id']
                new_id = f'AG_{self.next_agency_id}'
                self.next_agency_id += 1
                self.agency_map[source_name][old_id] = new_id

                self.agencies.append({
                    'agency_id': new_id,
                    'agency_name': row['agency_name'],
                    'agency_url': row.get('agency_url', ''),
                    'agency_timezone': row.get('agency_timezone', 'Europe/Prague'),
                    'agency_lang': row.get('agency_lang', 'cs')
                })

    def _load_stops(self, source_dir: Path, source_name: str):
        """Načte stops s deduplikací."""
        file_path = source_dir / 'stops.txt'
        if not file_path.exists():
            return

        new_stops = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['stop_id']
                stop_name = row['stop_name']

                # Deduplikace podle názvu
                if stop_name in self.stop_names:
                    new_id = self.stop_names[stop_name]
                else:
                    new_id = f'ST_{self.next_stop_id}'
                    self.next_stop_id += 1
                    self.stop_names[stop_name] = new_id
                    new_stops += 1

                    self.stops.append({
                        'stop_id': new_id,
                        'stop_name': stop_name,
                        'stop_lat': row.get('stop_lat', '0.0'),
                        'stop_lon': row.get('stop_lon', '0.0')
                    })

                self.stop_map[source_name][old_id] = new_id

        print(f"  Zastávky: +{new_stops} nových")

    def _load_routes(self, source_dir: Path, source_name: str):
        """Načte routes s kategorizací."""
        file_path = source_dir / 'routes.txt'
        if not file_path.exists():
            return

        mhd_count = 0
        regional_count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['route_id']
                new_id = f'RT_{self.next_route_id}'
                self.next_route_id += 1
                self.route_map[source_name][old_id] = new_id

                agency_old = row.get('agency_id', '')
                agency_new = self.agency_map[source_name].get(agency_old, '')

                route_data = {
                    'route_id': new_id,
                    'agency_id': agency_new,
                    'route_short_name': row.get('route_short_name', ''),
                    'route_long_name': row.get('route_long_name', ''),
                    'route_type': row.get('route_type', '3'),
                    '_is_mhd': False  # Internal flag
                }

                # Kategorizace
                if self._is_mhd_route(
                    row.get('route_short_name', ''),
                    row.get('route_type', '3'),
                    row.get('route_long_name', '')
                ):
                    route_data['_is_mhd'] = True
                    self.routes_mhd.append(route_data)
                    mhd_count += 1
                else:
                    self.routes_regional.append(route_data)
                    regional_count += 1

        print(f"  Linky: +{mhd_count} MHD, +{regional_count} regionální")

    def _load_calendar(self, source_dir: Path, source_name: str):
        """Načte calendar."""
        file_path = source_dir / 'calendar.txt'
        if not file_path.exists():
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['service_id']
                new_id = f'SV_{self.next_service_id}'
                self.next_service_id += 1
                self.service_map[source_name][old_id] = new_id

    def _load_calendar_dates(self, source_dir: Path, source_name: str):
        """Načte calendar dates."""
        file_path = source_dir / 'calendar_dates.txt'
        if not file_path.exists():
            return

        count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                service_old = row['service_id']
                service_new = self.service_map[source_name].get(service_old, f'SV_{self.next_service_id}')

                if service_old not in self.service_map[source_name]:
                    self.service_map[source_name][service_old] = service_new
                    self.next_service_id += 1

                self.calendar_dates.append({
                    'service_id': service_new,
                    'date': row['date'],
                    'exception_type': row.get('exception_type', '1')
                })
                count += 1

        print(f"  Calendar dates: +{count}")

    def _load_trips(self, source_dir: Path, source_name: str):
        """Načte trips s kategorizací."""
        file_path = source_dir / 'trips.txt'
        if not file_path.exists():
            return

        mhd_count = 0
        regional_count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['trip_id']
                new_id = f'TR_{self.next_trip_id}'
                self.next_trip_id += 1
                self.trip_map[source_name][old_id] = new_id

                route_old = row.get('route_id', '')
                route_new = self.route_map[source_name].get(route_old, '')

                service_old = row.get('service_id', '')
                service_new = self.service_map[source_name].get(service_old, '')

                trip_data = {
                    'trip_id': new_id,
                    'route_id': route_new,
                    'service_id': service_new
                }

                # Zjisti, jestli je route MHD
                is_mhd = any(r['route_id'] == route_new and r.get('_is_mhd') for r in self.routes_mhd)

                if is_mhd:
                    self.trips_mhd.append(trip_data)
                    self.mhd_trip_ids.add(new_id)
                    mhd_count += 1
                else:
                    self.trips_regional.append(trip_data)
                    regional_count += 1

        print(f"  Spoje: +{mhd_count} MHD, +{regional_count} regionální")

    def _is_mhd_route(self, route_name: str, route_type: str, route_long_name: str) -> bool:
        """Určí, jestli je linka MHD nebo regionální."""
        route_type = str(route_type)

        # Tramvaje a metro - vždy MHD
        if route_type in ['0', '1']:
            return True

        # Vlaky - většinou regionální
        if route_type == '2':
            return False

        # Autobusy - podle čísla linky
        if route_type == '3':
            if route_name.isdigit() and len(route_name) <= 3:
                return True
            if route_name.startswith('N') and len(route_name) <= 3:
                return True

        return False

    def process_stop_times(self, source_dir: Path, source_name: str, output_dir: Path):
        """Zpracuje stop_times průběžně bez načítání do paměti."""
        file_path = source_dir / 'stop_times.txt'
        if not file_path.exists():
            return

        print(f"  Stop times ({source_name}): zpracovávám", end='', flush=True)

        # Otevři výstupní soubory
        mhd_file = output_dir / 'mhd' / 'stop_times.txt'
        regional_file = output_dir / 'regional' / 'stop_times.txt'
        merged_file = output_dir / 'merged' / 'stop_times.txt'

        mhd_count = 0
        regional_count = 0
        processed = 0

        with open(file_path, 'r', encoding='utf-8') as f_in:
            reader = csv.DictReader(f_in)

            # Otevři výstupní soubory v append módu
            with open(mhd_file, 'a', encoding='utf-8', newline='') as f_mhd, \
                 open(regional_file, 'a', encoding='utf-8', newline='') as f_regional, \
                 open(merged_file, 'a', encoding='utf-8', newline='') as f_merged:

                writer_mhd = csv.DictWriter(f_mhd, fieldnames=['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'])
                writer_regional = csv.DictWriter(f_regional, fieldnames=['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'])
                writer_merged = csv.DictWriter(f_merged, fieldnames=['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'])

                for row in reader:
                    trip_old = row['trip_id']
                    trip_new = self.trip_map[source_name].get(trip_old)

                    if not trip_new:
                        continue

                    stop_old = row['stop_id']
                    stop_new = self.stop_map[source_name].get(stop_old)

                    if not stop_new:
                        continue

                    st_data = {
                        'trip_id': trip_new,
                        'stop_id': stop_new,
                        'stop_sequence': row.get('stop_sequence', '0'),
                        'arrival_time': row.get('arrival_time', '00:00:00'),
                        'departure_time': row.get('departure_time', '00:00:00')
                    }

                    # Zjisti, jestli je trip MHD
                    is_mhd = trip_new in self.mhd_trip_ids

                    if is_mhd:
                        writer_mhd.writerow(st_data)
                        mhd_count += 1
                    else:
                        writer_regional.writerow(st_data)
                        regional_count += 1

                    writer_merged.writerow(st_data)

                    processed += 1
                    if processed % 100000 == 0:
                        print('.', end='', flush=True)

        print(f" +{mhd_count} MHD, +{regional_count} regionální")

    def export_metadata(self, output_dir: Path):
        """Exportuje metadata (vše kromě stop_times)."""
        print("\n" + "="*80)
        print("EXPORT METADAT")
        print("="*80)

        # Vytvoř výstupní adresáře
        mhd_dir = output_dir / 'mhd'
        regional_dir = output_dir / 'regional'
        merged_dir = output_dir / 'merged'

        mhd_dir.mkdir(parents=True, exist_ok=True)
        regional_dir.mkdir(parents=True, exist_ok=True)
        merged_dir.mkdir(parents=True, exist_ok=True)

        # Export společných souborů
        print("\nExport společných souborů...")

        # Agency
        self._write_csv(mhd_dir / 'agency.txt', self.agencies, ['agency_id', 'agency_name', 'agency_url', 'agency_timezone', 'agency_lang'])
        self._write_csv(regional_dir / 'agency.txt', self.agencies, ['agency_id', 'agency_name', 'agency_url', 'agency_timezone', 'agency_lang'])
        self._write_csv(merged_dir / 'agency.txt', self.agencies, ['agency_id', 'agency_name', 'agency_url', 'agency_timezone', 'agency_lang'])
        print(f"  agency.txt: {len(self.agencies)} agencies")

        # Stops
        self._write_csv(mhd_dir / 'stops.txt', self.stops, ['stop_id', 'stop_name', 'stop_lat', 'stop_lon'])
        self._write_csv(regional_dir / 'stops.txt', self.stops, ['stop_id', 'stop_name', 'stop_lat', 'stop_lon'])
        self._write_csv(merged_dir / 'stops.txt', self.stops, ['stop_id', 'stop_name', 'stop_lat', 'stop_lon'])
        print(f"  stops.txt: {len(self.stops)} zastávek")

        # Calendar dates
        if self.calendar_dates:
            self._write_csv(merged_dir / 'calendar_dates.txt', self.calendar_dates, ['service_id', 'date', 'exception_type'])
            print(f"  calendar_dates.txt: {len(self.calendar_dates)} výjimek")

        # Export MHD
        print("\nExport MHD dat...")

        # Odstraň internal flag
        routes_mhd_clean = [{k: v for k, v in r.items() if not k.startswith('_')} for r in self.routes_mhd]

        self._write_csv(mhd_dir / 'routes.txt', routes_mhd_clean, ['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type'])
        print(f"  routes.txt: {len(routes_mhd_clean)} linek")

        self._write_csv(mhd_dir / 'trips.txt', self.trips_mhd, ['trip_id', 'route_id', 'service_id'])
        print(f"  trips.txt: {len(self.trips_mhd)} spojů")

        # Vytvoř prázdný stop_times.txt s hlavičkou
        self._write_csv(mhd_dir / 'stop_times.txt', [], ['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'])

        # Export regionální
        print("\nExport regionálních dat...")

        routes_regional_clean = [{k: v for k, v in r.items() if not k.startswith('_')} for r in self.routes_regional]

        self._write_csv(regional_dir / 'routes.txt', routes_regional_clean, ['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type'])
        print(f"  routes.txt: {len(routes_regional_clean)} linek")

        self._write_csv(regional_dir / 'trips.txt', self.trips_regional, ['trip_id', 'route_id', 'service_id'])
        print(f"  trips.txt: {len(self.trips_regional)} spojů")

        self._write_csv(regional_dir / 'stop_times.txt', [], ['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'])

        # Export merged
        print("\nExport kompletního datasetu...")

        all_routes = routes_mhd_clean + routes_regional_clean
        self._write_csv(merged_dir / 'routes.txt', all_routes, ['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type'])
        print(f"  routes.txt: {len(all_routes)} linek")

        all_trips = self.trips_mhd + self.trips_regional
        self._write_csv(merged_dir / 'trips.txt', all_trips, ['trip_id', 'route_id', 'service_id'])
        print(f"  trips.txt: {len(all_trips)} spojů")

        self._write_csv(merged_dir / 'stop_times.txt', [], ['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'])

    def _write_csv(self, file_path: Path, data: List[Dict], fieldnames: List[str]):
        """Zapíše CSV soubor."""
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)


def main():
    # Cesty
    project_dir = Path(__file__).parent.parent
    tt_converted_dir = project_dir / 'data' / 'mhd'
    gtfs_cr_dir = Path('/Users/imac/Github/stredniskoly/data/GTFS_CR')
    pid_dir = Path('/Users/imac/Github/stredniskoly/data/PID')
    output_dir = project_dir / 'data'

    # Vytvoř integrátor
    integrator = GTFSIntegratorFast()

    print("="*80)
    print("INTEGRACE VŠECH GTFS DAT")
    print("="*80)

    sources = []

    # Načti metadata ze zdrojů
    if tt_converted_dir.exists():
        integrator.load_source(tt_converted_dir, 'TT-converted')
        sources.append(('TT-converted', tt_converted_dir))

    if gtfs_cr_dir.exists():
        integrator.load_source(gtfs_cr_dir, 'GTFS_CR')
        sources.append(('GTFS_CR', gtfs_cr_dir))

    if pid_dir.exists():
        integrator.load_source(pid_dir, 'PID')
        sources.append(('PID', pid_dir))

    # Export metadat
    integrator.export_metadata(output_dir)

    # Zpracuj stop_times průběžně
    print("\n" + "="*80)
    print("ZPRACOVÁNÍ STOP_TIMES")
    print("="*80)

    for source_name, source_dir in sources:
        integrator.process_stop_times(source_dir, source_name, output_dir)

    print("\n" + "="*80)
    print("HOTOVO")
    print("="*80)
    print(f"\nData exportována do:")
    print(f"  - {output_dir / 'mhd'} (MHD)")
    print(f"  - {output_dir / 'regional'} (Regionální)")
    print(f"  - {output_dir / 'merged'} (Vše dohromady)")


if __name__ == '__main__':
    main()
