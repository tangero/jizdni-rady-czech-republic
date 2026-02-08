#!/usr/bin/env python3
"""
Optimalizovaná integrace všech GTFS dat do jednoho datasetu.
Využívá pandas pro rychlejší zpracování velkých CSV souborů.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Set
import sys

class GTFSIntegratorOptimized:
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

        # Výsledné DataFrames
        self.agencies = []
        self.stops = []
        self.routes_mhd = []
        self.routes_regional = []
        self.trips_mhd = []
        self.trips_regional = []
        self.stop_times_mhd = []
        self.stop_times_regional = []
        self.calendar_dates = []

    def load_source(self, source_dir: Path, source_name: str):
        """Načte jeden GTFS zdroj a remapuje ID."""
        print(f"\nNačítám: {source_name}")

        self.agency_map[source_name] = {}
        self.stop_map[source_name] = {}
        self.route_map[source_name] = {}
        self.trip_map[source_name] = {}
        self.service_map[source_name] = {}

        # 1. Agency
        agency_file = source_dir / 'agency.txt'
        if agency_file.exists():
            df = pd.read_csv(agency_file, dtype=str)
            for _, row in df.iterrows():
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

        # 2. Stops - s deduplikací
        stops_file = source_dir / 'stops.txt'
        if stops_file.exists():
            df = pd.read_csv(stops_file, dtype=str)
            new_stops = 0

            for _, row in df.iterrows():
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

        # 3. Routes - kategorizace na MHD vs regionální
        routes_file = source_dir / 'routes.txt'
        if routes_file.exists():
            df = pd.read_csv(routes_file, dtype=str)
            mhd_count = 0
            regional_count = 0

            for _, row in df.iterrows():
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
                    'route_type': row.get('route_type', '3')
                }

                # Kategorizace
                if self._is_mhd_route(
                    row.get('route_short_name', ''),
                    row.get('route_type', '3'),
                    row.get('route_long_name', '')
                ):
                    self.routes_mhd.append(route_data)
                    mhd_count += 1
                else:
                    self.routes_regional.append(route_data)
                    regional_count += 1

            print(f"  Linky: +{mhd_count} MHD, +{regional_count} regionální")

        # 4. Calendar
        calendar_file = source_dir / 'calendar.txt'
        if calendar_file.exists():
            df = pd.read_csv(calendar_file, dtype=str)
            for _, row in df.iterrows():
                old_id = row['service_id']
                new_id = f'SV_{self.next_service_id}'
                self.next_service_id += 1
                self.service_map[source_name][old_id] = new_id

        # 5. Calendar dates
        calendar_dates_file = source_dir / 'calendar_dates.txt'
        if calendar_dates_file.exists():
            df = pd.read_csv(calendar_dates_file, dtype=str)
            print(f"  Calendar dates: +{len(df)}")

            for _, row in df.iterrows():
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

        # 6. Trips - kategorizace podle route
        trips_file = source_dir / 'trips.txt'
        if trips_file.exists():
            df = pd.read_csv(trips_file, dtype=str)
            mhd_count = 0
            regional_count = 0

            for _, row in df.iterrows():
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

                # Zjisti, jestli je route MHD nebo regionální
                is_mhd = any(r['route_id'] == route_new for r in self.routes_mhd)

                if is_mhd:
                    self.trips_mhd.append(trip_data)
                    mhd_count += 1
                else:
                    self.trips_regional.append(trip_data)
                    regional_count += 1

            print(f"  Spoje: +{mhd_count} MHD, +{regional_count} regionální")

        # 7. Stop times - chunked processing pro velké soubory
        stop_times_file = source_dir / 'stop_times.txt'
        if stop_times_file.exists():
            print(f"  Stop times: načítám", end='', flush=True)

            mhd_count = 0
            regional_count = 0

            # Chunked reading
            chunk_size = 100000
            for chunk in pd.read_csv(stop_times_file, dtype=str, chunksize=chunk_size):
                print('.', end='', flush=True)

                for _, row in chunk.iterrows():
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

                    # Zjisti, jestli je trip MHD nebo regionální
                    is_mhd = any(t['trip_id'] == trip_new for t in self.trips_mhd)

                    if is_mhd:
                        self.stop_times_mhd.append(st_data)
                        mhd_count += 1
                    else:
                        self.stop_times_regional.append(st_data)
                        regional_count += 1

            print(f" +{mhd_count} MHD, +{regional_count} regionální")

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
            # Pokud je číslo 1-999, je to pravděpodobně MHD
            if route_name.isdigit() and len(route_name) <= 3:
                return True

            # Noční linky (začínají N)
            if route_name.startswith('N') and len(route_name) <= 3:
                return True

        return False

    def export_datasets(self, output_dir: Path):
        """Exportuje integrovaná data do tří kategorií."""
        print("\n" + "="*80)
        print("EXPORT DAT")
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
        df = pd.DataFrame(self.agencies)
        df.to_csv(mhd_dir / 'agency.txt', index=False)
        df.to_csv(regional_dir / 'agency.txt', index=False)
        df.to_csv(merged_dir / 'agency.txt', index=False)
        print(f"  agency.txt: {len(df)} agencies")

        # Stops
        df = pd.DataFrame(self.stops)
        df.to_csv(mhd_dir / 'stops.txt', index=False)
        df.to_csv(regional_dir / 'stops.txt', index=False)
        df.to_csv(merged_dir / 'stops.txt', index=False)
        print(f"  stops.txt: {len(df)} zastávek")

        # Calendar dates
        if self.calendar_dates:
            df = pd.DataFrame(self.calendar_dates)
            df.to_csv(merged_dir / 'calendar_dates.txt', index=False)
            print(f"  calendar_dates.txt: {len(df)} výjimek")

        # Export MHD
        print("\nExport MHD dat...")

        df = pd.DataFrame(self.routes_mhd)
        df.to_csv(mhd_dir / 'routes.txt', index=False)
        df.to_csv(merged_dir / 'routes_mhd.txt', index=False)
        print(f"  routes.txt: {len(df)} linek")

        df = pd.DataFrame(self.trips_mhd)
        df.to_csv(mhd_dir / 'trips.txt', index=False)
        df.to_csv(merged_dir / 'trips_mhd.txt', index=False)
        print(f"  trips.txt: {len(df)} spojů")

        df = pd.DataFrame(self.stop_times_mhd)
        df.to_csv(mhd_dir / 'stop_times.txt', index=False)
        df.to_csv(merged_dir / 'stop_times_mhd.txt', index=False)
        print(f"  stop_times.txt: {len(df)} zastávek spojů")

        # Export regionální
        print("\nExport regionálních dat...")

        df = pd.DataFrame(self.routes_regional)
        df.to_csv(regional_dir / 'routes.txt', index=False)
        df.to_csv(merged_dir / 'routes_regional.txt', index=False)
        print(f"  routes.txt: {len(df)} linek")

        df = pd.DataFrame(self.trips_regional)
        df.to_csv(regional_dir / 'trips.txt', index=False)
        df.to_csv(merged_dir / 'trips_regional.txt', index=False)
        print(f"  trips.txt: {len(df)} spojů")

        df = pd.DataFrame(self.stop_times_regional)
        df.to_csv(regional_dir / 'stop_times.txt', index=False)
        df.to_csv(merged_dir / 'stop_times_regional.txt', index=False)
        print(f"  stop_times.txt: {len(df)} zastávek spojů")

        # Export merged (kompletní dataset)
        print("\nExport kompletního datasetu...")

        all_routes = self.routes_mhd + self.routes_regional
        df = pd.DataFrame(all_routes)
        df.to_csv(merged_dir / 'routes.txt', index=False)
        print(f"  routes.txt: {len(df)} linek")

        all_trips = self.trips_mhd + self.trips_regional
        df = pd.DataFrame(all_trips)
        df.to_csv(merged_dir / 'trips.txt', index=False)
        print(f"  trips.txt: {len(df)} spojů")

        all_stop_times = self.stop_times_mhd + self.stop_times_regional
        df = pd.DataFrame(all_stop_times)
        df.to_csv(merged_dir / 'stop_times.txt', index=False)
        print(f"  stop_times.txt: {len(df)} zastávek spojů")

        print("\n" + "="*80)
        print("HOTOVO")
        print("="*80)
        print(f"\nData exportována do:")
        print(f"  - {mhd_dir} (MHD)")
        print(f"  - {regional_dir} (Regionální)")
        print(f"  - {merged_dir} (Vše dohromady)")


def main():
    # Cesty
    project_dir = Path(__file__).parent.parent
    tt_converted_dir = project_dir / 'data' / 'mhd'
    gtfs_cr_dir = Path('/Users/imac/Github/stredniskoly/data/GTFS_CR')
    pid_dir = Path('/Users/imac/Github/stredniskoly/data/PID')
    output_dir = project_dir / 'data'

    # Vytvoř integrátor
    integrator = GTFSIntegratorOptimized()

    print("="*80)
    print("INTEGRACE VŠECH GTFS DAT")
    print("="*80)

    # Načti zdroje
    if tt_converted_dir.exists():
        integrator.load_source(tt_converted_dir, 'TT-converted')

    if gtfs_cr_dir.exists():
        integrator.load_source(gtfs_cr_dir, 'GTFS_CR')

    if pid_dir.exists():
        integrator.load_source(pid_dir, 'PID')

    # Export
    integrator.export_datasets(output_dir)


if __name__ == '__main__':
    main()
