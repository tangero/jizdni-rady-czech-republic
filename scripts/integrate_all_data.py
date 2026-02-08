#!/usr/bin/env python3
"""
Integrace všech GTFS dat do jednotné struktury podle logiky projektu.
"""

import csv
from pathlib import Path
from collections import defaultdict
import sys


class GTFSIntegrator:
    """Integruje více GTFS zdrojů do jednotné struktury."""

    def __init__(self):
        self.agencies = []
        self.stops = {}  # stop_id -> stop_data (deduplikace)
        self.routes_mhd = []
        self.routes_regional = []
        self.trips_mhd = []
        self.trips_regional = []
        self.stop_times_mhd = []
        self.stop_times_regional = []
        self.calendars = {}  # service_id -> calendar_data (deduplikace)
        self.calendar_dates = []
        self.transfers = []

        self.agency_id_map = {}  # Mapování starých ID na nové
        self.route_id_map = {}
        self.trip_id_map = {}
        self.stop_id_map = {}
        self.service_id_map = {}

        self.next_agency_id = 1
        self.next_route_id = 1
        self.next_trip_id = 1
        self.next_stop_id = 1
        self.next_service_id = 1

    def load_source(self, source_dir: Path, source_name: str):
        """Načti jeden GTFS zdroj."""
        print(f"\nNačítám: {source_name}")

        # Agency
        self._load_agencies(source_dir, source_name)

        # Stops
        self._load_stops(source_dir, source_name)

        # Routes & kategorizace
        self._load_routes(source_dir, source_name)

        # Calendar
        self._load_calendar(source_dir, source_name)

        # Calendar dates
        self._load_calendar_dates(source_dir, source_name)

        # Trips
        self._load_trips(source_dir, source_name)

        # Stop times
        self._load_stop_times(source_dir, source_name)

        # Transfers
        self._load_transfers(source_dir, source_name)

    def _load_agencies(self, source_dir, source_name):
        """Načti agencies s novými ID."""
        agency_file = source_dir / 'agency.txt'
        if not agency_file.exists():
            return

        with open(agency_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['agency_id']
                new_id = f"AG_{self.next_agency_id}"
                self.next_agency_id += 1

                self.agency_id_map[f"{source_name}:{old_id}"] = new_id

                self.agencies.append({
                    'agency_id': new_id,
                    'agency_name': row['agency_name'],
                    'agency_url': row.get('agency_url', 'http://example.com'),
                    'agency_timezone': row.get('agency_timezone', 'Europe/Prague'),
                    'agency_lang': row.get('agency_lang', 'cs')
                })

    def _load_stops(self, source_dir, source_name):
        """Načti zastávky (deduplikace podle názvu)."""
        stops_file = source_dir / 'stops.txt'
        if not stops_file.exists():
            return

        count = 0
        with open(stops_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['stop_id']
                stop_name = row['stop_name']

                # Deduplikace podle názvu (zjednodušeně)
                if stop_name in self.stops:
                    # Zastávka už existuje, použij existující ID
                    self.stop_id_map[f"{source_name}:{old_id}"] = self.stops[stop_name]['stop_id']
                else:
                    # Nová zastávka
                    new_id = f"ST_{self.next_stop_id}"
                    self.next_stop_id += 1

                    self.stop_id_map[f"{source_name}:{old_id}"] = new_id

                    self.stops[stop_name] = {
                        'stop_id': new_id,
                        'stop_name': stop_name,
                        'stop_lat': row.get('stop_lat', '0.0'),
                        'stop_lon': row.get('stop_lon', '0.0')
                    }
                    count += 1

        print(f"  Zastávky: +{count} nových")

    def _load_routes(self, source_dir, source_name):
        """Načti linky a kategorizuj je."""
        routes_file = source_dir / 'routes.txt'
        if not routes_file.exists():
            return

        mhd_count = 0
        regional_count = 0

        with open(routes_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['route_id']
                new_id = f"RT_{self.next_route_id}"
                self.next_route_id += 1

                self.route_id_map[f"{source_name}:{old_id}"] = new_id

                # Mapuj agency_id
                old_agency_id = row['agency_id']
                new_agency_id = self.agency_id_map.get(f"{source_name}:{old_agency_id}", old_agency_id)

                route_type = int(row['route_type'])
                route_name = row.get('route_short_name', row.get('route_long_name', ''))

                route_data = {
                    'route_id': new_id,
                    'agency_id': new_agency_id,
                    'route_short_name': route_name,
                    'route_long_name': row.get('route_long_name', route_name),
                    'route_type': route_type
                }

                # Kategorizace: MHD vs regionální
                # MHD = městské linky (většinou route_type 3=bus, 0=tram, 1=metro)
                # Regionální = dálkové (vlaky, meziměstské autobusy)

                is_mhd = self._is_mhd_route(route_name, route_type, row.get('agency_name', ''))

                if is_mhd:
                    self.routes_mhd.append(route_data)
                    mhd_count += 1
                else:
                    self.routes_regional.append(route_data)
                    regional_count += 1

        print(f"  Linky: +{mhd_count} MHD, +{regional_count} regionální")

    def _is_mhd_route(self, route_name, route_type, agency_name):
        """Určí, zda je linka MHD nebo regionální."""
        # Tramvaje a metro jsou vždy MHD
        if route_type in [0, 1]:  # tram, metro
            return True

        # Vlaky jsou většinou regionální
        if route_type == 2:  # rail
            return False

        # Autobusy: rozhodnutí podle názvu a kontextu
        if route_type == 3:  # bus
            # Číselné linky jsou často MHD
            if route_name.isdigit() and len(route_name) <= 3:
                return True

            # Linky s písmeny jsou často MHD
            if len(route_name) <= 2:
                return True

            # Regionální mají často delší názvy
            return False

        # Default: regionální
        return False

    def _load_calendar(self, source_dir, source_name):
        """Načti kalendáře."""
        calendar_file = source_dir / 'calendar.txt'
        if not calendar_file.exists():
            return

        with open(calendar_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['service_id']

                # Deduplikace kalendářů podle dat
                cal_key = (row['monday'], row['tuesday'], row['wednesday'],
                          row['thursday'], row['friday'], row['saturday'], row['sunday'],
                          row['start_date'], row['end_date'])

                if cal_key in self.calendars:
                    self.service_id_map[f"{source_name}:{old_id}"] = self.calendars[cal_key]['service_id']
                else:
                    new_id = f"SV_{self.next_service_id}"
                    self.next_service_id += 1

                    self.service_id_map[f"{source_name}:{old_id}"] = new_id

                    self.calendars[cal_key] = {
                        'service_id': new_id,
                        'monday': row['monday'],
                        'tuesday': row['tuesday'],
                        'wednesday': row['wednesday'],
                        'thursday': row['thursday'],
                        'friday': row['friday'],
                        'saturday': row['saturday'],
                        'sunday': row['sunday'],
                        'start_date': row['start_date'],
                        'end_date': row['end_date']
                    }

    def _load_calendar_dates(self, source_dir, source_name):
        """Načti calendar_dates."""
        cal_dates_file = source_dir / 'calendar_dates.txt'
        if not cal_dates_file.exists():
            return

        count = 0
        with open(cal_dates_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_service_id = row['service_id']
                new_service_id = self.service_id_map.get(f"{source_name}:{old_service_id}", old_service_id)

                self.calendar_dates.append({
                    'service_id': new_service_id,
                    'date': row['date'],
                    'exception_type': row['exception_type']
                })
                count += 1

        if count > 0:
            print(f"  Calendar dates: +{count}")

    def _load_trips(self, source_dir, source_name):
        """Načti spoje."""
        trips_file = source_dir / 'trips.txt'
        if not trips_file.exists():
            return

        mhd_count = 0
        regional_count = 0

        with open(trips_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['trip_id']
                new_id = f"TR_{self.next_trip_id}"
                self.next_trip_id += 1

                self.trip_id_map[f"{source_name}:{old_id}"] = new_id

                old_route_id = row['route_id']
                new_route_id = self.route_id_map.get(f"{source_name}:{old_route_id}", old_route_id)

                old_service_id = row['service_id']
                new_service_id = self.service_id_map.get(f"{source_name}:{old_service_id}", old_service_id)

                trip_data = {
                    'trip_id': new_id,
                    'route_id': new_route_id,
                    'service_id': new_service_id
                }

                # Kategorizuj podle route
                route_key = f"{source_name}:{old_route_id}"
                is_mhd = new_route_id in [r['route_id'] for r in self.routes_mhd]

                if is_mhd:
                    self.trips_mhd.append(trip_data)
                    mhd_count += 1
                else:
                    self.trips_regional.append(trip_data)
                    regional_count += 1

        print(f"  Spoje: +{mhd_count} MHD, +{regional_count} regionální")

    def _load_stop_times(self, source_dir, source_name):
        """Načti stop_times."""
        stop_times_file = source_dir / 'stop_times.txt'
        if not stop_times_file.exists():
            return

        print(f"  Stop times: načítám...", end='', flush=True)

        mhd_count = 0
        regional_count = 0

        # Načti v chunks pro velké soubory
        chunk_size = 10000
        chunk = []

        with open(stop_times_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_trip_id = row['trip_id']
                new_trip_id = self.trip_id_map.get(f"{source_name}:{old_trip_id}", old_trip_id)

                old_stop_id = row['stop_id']
                new_stop_id = self.stop_id_map.get(f"{source_name}:{old_stop_id}", old_stop_id)

                st_data = {
                    'trip_id': new_trip_id,
                    'stop_id': new_stop_id,
                    'stop_sequence': row['stop_sequence'],
                    'arrival_time': row['arrival_time'],
                    'departure_time': row['departure_time']
                }

                # Kategorizuj podle trip
                is_mhd = new_trip_id in [t['trip_id'] for t in self.trips_mhd]

                if is_mhd:
                    self.stop_times_mhd.append(st_data)
                    mhd_count += 1
                else:
                    self.stop_times_regional.append(st_data)
                    regional_count += 1

                # Průběžný výpis
                if (mhd_count + regional_count) % chunk_size == 0:
                    print('.', end='', flush=True)

        print(f" +{mhd_count} MHD, +{regional_count} regionální")

    def _load_transfers(self, source_dir, source_name):
        """Načti transfers."""
        transfers_file = source_dir / 'transfers.txt'
        if not transfers_file.exists():
            return

        count = 0
        with open(transfers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_from_stop = row['from_stop_id']
                new_from_stop = self.stop_id_map.get(f"{source_name}:{old_from_stop}", old_from_stop)

                old_to_stop = row['to_stop_id']
                new_to_stop = self.stop_id_map.get(f"{source_name}:{old_to_stop}", old_to_stop)

                self.transfers.append({
                    'from_stop_id': new_from_stop,
                    'to_stop_id': new_to_stop,
                    'transfer_type': row['transfer_type'],
                    'min_transfer_time': row.get('min_transfer_time', '')
                })
                count += 1

        if count > 0:
            print(f"  Transfers: +{count}")

    def export(self, output_dir: Path):
        """Exportuj integrovaná data."""
        print("\n=== EXPORT ===")

        # MHD
        mhd_dir = output_dir / 'mhd'
        mhd_dir.mkdir(parents=True, exist_ok=True)
        self._export_category(mhd_dir, 'MHD',
                             self.routes_mhd, self.trips_mhd, self.stop_times_mhd)

        # Regionální
        regional_dir = output_dir / 'regional'
        regional_dir.mkdir(parents=True, exist_ok=True)
        self._export_category(regional_dir, 'Regionální',
                             self.routes_regional, self.trips_regional, self.stop_times_regional)

        # Merged (všechno dohromady)
        merged_dir = output_dir / 'merged'
        merged_dir.mkdir(parents=True, exist_ok=True)
        self._export_merged(merged_dir)

    def _export_category(self, output_dir, category_name, routes, trips, stop_times):
        """Export jedné kategorie."""
        print(f"\n{category_name} → {output_dir}/")

        # agency.txt
        self._write_csv(output_dir / 'agency.txt', self.agencies,
                       ['agency_id', 'agency_name', 'agency_url', 'agency_timezone', 'agency_lang'])
        print(f"  ✓ agency.txt ({len(self.agencies)} agencies)")

        # stops.txt
        stops_list = list(self.stops.values())
        self._write_csv(output_dir / 'stops.txt', stops_list,
                       ['stop_id', 'stop_name', 'stop_lat', 'stop_lon'])
        print(f"  ✓ stops.txt ({len(stops_list)} zastávek)")

        # routes.txt
        self._write_csv(output_dir / 'routes.txt', routes,
                       ['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type'])
        print(f"  ✓ routes.txt ({len(routes)} linek)")

        # trips.txt
        self._write_csv(output_dir / 'trips.txt', trips,
                       ['trip_id', 'route_id', 'service_id'])
        print(f"  ✓ trips.txt ({len(trips)} spojů)")

        # stop_times.txt
        self._write_csv(output_dir / 'stop_times.txt', stop_times,
                       ['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'])
        print(f"  ✓ stop_times.txt ({len(stop_times)} záznamů)")

        # calendar.txt
        calendar_list = list(self.calendars.values())
        self._write_csv(output_dir / 'calendar.txt', calendar_list,
                       ['service_id', 'monday', 'tuesday', 'wednesday', 'thursday',
                        'friday', 'saturday', 'sunday', 'start_date', 'end_date'])
        print(f"  ✓ calendar.txt ({len(calendar_list)} kalendářů)")

        # calendar_dates.txt
        if self.calendar_dates:
            self._write_csv(output_dir / 'calendar_dates.txt', self.calendar_dates,
                           ['service_id', 'date', 'exception_type'])
            print(f"  ✓ calendar_dates.txt ({len(self.calendar_dates)} výjimek)")

        # transfers.txt
        if self.transfers:
            self._write_csv(output_dir / 'transfers.txt', self.transfers,
                           ['from_stop_id', 'to_stop_id', 'transfer_type', 'min_transfer_time'])
            print(f"  ✓ transfers.txt ({len(self.transfers)} přestupů)")

    def _export_merged(self, output_dir):
        """Export sloučených dat."""
        all_routes = self.routes_mhd + self.routes_regional
        all_trips = self.trips_mhd + self.trips_regional
        all_stop_times = self.stop_times_mhd + self.stop_times_regional

        self._export_category(output_dir, 'Merged', all_routes, all_trips, all_stop_times)

    def _write_csv(self, filepath, data, fieldnames):
        """Zapiš CSV soubor."""
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)


def main():
    print("="*80)
    print("INTEGRACE VŠECH GTFS DAT")
    print("="*80)

    integrator = GTFSIntegrator()

    # Načti všechny zdroje
    sources = [
        (Path('/Users/imac/Github/jizdni-rady-czech-republic/data/mhd'), 'TT-converted'),
        (Path('/Users/imac/Github/stredniskoly/data/GTFS_CR'), 'GTFS_CR'),
        (Path('/Users/imac/Github/stredniskoly/data/PID'), 'PID'),
    ]

    for source_dir, source_name in sources:
        if source_dir.exists():
            integrator.load_source(source_dir, source_name)
        else:
            print(f"⚠️  {source_name}: nenalezen ({source_dir})")

    # Export
    output_dir = Path('/Users/imac/Github/jizdni-rady-czech-republic/data')
    integrator.export(output_dir)

    print("\n" + "="*80)
    print("✅ INTEGRACE DOKONČENA")
    print("="*80)


if __name__ == '__main__':
    main()
