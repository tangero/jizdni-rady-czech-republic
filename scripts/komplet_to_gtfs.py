#!/usr/bin/env python3
"""
KOMPLET → GTFS Master Converter
Komplexní konverze všech CHAPS .tt souborů do GTFS standardu s pokročilým logováním.

Zpracovává:
- Data1/ - Vlaky (VL)
- Data2/ - Meziměstské autobusy (BUS)
- Data3/ - Městská MHD (MHD)

Output:
- data/GTFS_CZ/VL/ - GTFS pro vlaky
- data/GTFS_CZ/BUS/ - GTFS pro autobusy
- data/GTFS_CZ/MHD/ - GTFS pro MHD
- logs/ - Detailní logy
"""

import sys
import json
import csv
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import traceback

# Import dekodéru
sys.path.insert(0, str(Path(__file__).parent))
from tt_decoder_v2 import TTDecoderV2


@dataclass
class DecodingStats:
    """Statistiky dekódování jednoho souboru."""
    filename: str
    category: str  # VL/BUS/MHD
    success: bool
    stops: int = 0
    trips: int = 0
    edges: int = 0
    error_message: str = ""
    offset_found: str = ""
    processing_time_ms: int = 0


@dataclass
class GTFSStats:
    """Globální GTFS statistiky."""
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    total_stops: int = 0
    total_routes: int = 0
    total_trips: int = 0
    total_stop_times: int = 0
    categories: Dict[str, int] = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = {'VL': 0, 'BUS': 0, 'MHD': 0}


class KompletToGTFS:
    """Master konvertor KOMPLET → GTFS."""

    def __init__(self, komplet_dir: Path, output_base_dir: Path, log_dir: Optional[Path] = None):
        self.komplet_dir = komplet_dir
        self.output_base_dir = output_base_dir

        # Vytvoř strukturu adresářů
        self.output_dirs = {
            'VL': output_base_dir / 'VL',
            'BUS': output_base_dir / 'BUS',
            'MHD': output_base_dir / 'MHD',
        }

        for dir_path in self.output_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        # Adresář pro intermediate JSON
        self.json_dir = output_base_dir / '_intermediate_json'
        self.json_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.log_dir = log_dir or Path('logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.setup_logging()

        # Statistiky
        self.decoding_stats: List[DecodingStats] = []
        self.gtfs_stats = GTFSStats()

        # GTFS data pro každou kategorii
        self.gtfs_data = {
            'VL': self._init_gtfs_structure(),
            'BUS': self._init_gtfs_structure(),
            'MHD': self._init_gtfs_structure(),
        }

        # ID counters per category
        self.counters = {
            'VL': {'stop': 1, 'route': 1, 'trip': 1},
            'BUS': {'stop': 1, 'route': 1, 'trip': 1},
            'MHD': {'stop': 1, 'route': 1, 'trip': 1},
        }

        # Stop mappings per category
        self.stop_mappings = {
            'VL': {},
            'BUS': {},
            'MHD': {},
        }

    def setup_logging(self):
        """Nastav pokročilý logging systém."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Main log - INFO level
        main_log = self.log_dir / f'komplet_to_gtfs_{timestamp}.log'

        # Error log - ERROR level
        error_log = self.log_dir / f'errors_{timestamp}.log'

        # Detail log - DEBUG level
        detail_log = self.log_dir / f'detail_{timestamp}.log'

        # Configure root logger
        self.logger = logging.getLogger('KompletToGTFS')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # Console handler - INFO
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)

        # Main file handler - INFO
        main_handler = logging.FileHandler(main_log, encoding='utf-8')
        main_handler.setLevel(logging.INFO)
        main_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        main_handler.setFormatter(main_formatter)

        # Error file handler - ERROR
        error_handler = logging.FileHandler(error_log, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s')
        error_handler.setFormatter(error_formatter)

        # Detail file handler - DEBUG
        detail_handler = logging.FileHandler(detail_log, encoding='utf-8')
        detail_handler.setLevel(logging.DEBUG)
        detail_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(funcName)s - %(message)s')
        detail_handler.setFormatter(detail_formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(main_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(detail_handler)

        self.logger.info("="*80)
        self.logger.info("KOMPLET → GTFS Conversion Started")
        self.logger.info("="*80)
        self.logger.info(f"Input:  {self.komplet_dir}")
        self.logger.info(f"Output: {self.output_base_dir}")
        self.logger.info(f"Logs:   {self.log_dir}")

    def _init_gtfs_structure(self) -> Dict:
        """Inicializuj prázdnou GTFS strukturu."""
        return {
            'agencies': [],
            'stops': [],
            'routes': [],
            'trips': [],
            'stop_times': [],
        }

    def convert(self) -> bool:
        """Hlavní konverzní pipeline."""
        try:
            # 1. Najdi všechny .tt soubory
            self.logger.info("\n" + "="*80)
            self.logger.info("Phase 1: Scanning for .tt files")
            self.logger.info("="*80)

            tt_files = self._scan_komplet_directory()

            if not tt_files:
                self.logger.error("No .tt files found!")
                return False

            self.gtfs_stats.total_files = sum(len(f) for f in tt_files.values())

            # 2. Dekóduj každý soubor
            self.logger.info("\n" + "="*80)
            self.logger.info("Phase 2: Decoding .tt files")
            self.logger.info("="*80)

            for category, files in tt_files.items():
                self.logger.info(f"\n[{category}] Processing {len(files)} files...")
                self._decode_category(category, files)

            # 3. Vytvoř GTFS strukturu
            self.logger.info("\n" + "="*80)
            self.logger.info("Phase 3: Building GTFS feeds")
            self.logger.info("="*80)

            self._build_gtfs_feeds()

            # 4. Export GTFS souborů
            self.logger.info("\n" + "="*80)
            self.logger.info("Phase 4: Exporting GTFS files")
            self.logger.info("="*80)

            self._export_gtfs_files()

            # 5. Generuj reporty
            self.logger.info("\n" + "="*80)
            self.logger.info("Phase 5: Generating reports")
            self.logger.info("="*80)

            self._generate_reports()

            self.logger.info("\n" + "="*80)
            self.logger.info("✅ CONVERSION COMPLETED SUCCESSFULLY")
            self.logger.info("="*80)

            return True

        except Exception as e:
            self.logger.error(f"Fatal error in conversion pipeline: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def _scan_komplet_directory(self) -> Dict[str, List[Path]]:
        """Skenuj KOMPLET adresář a rozděl soubory po kategoriích."""
        files = {
            'VL': [],
            'BUS': [],
            'MHD': [],
        }

        # Data1 - Vlaky
        data1 = self.komplet_dir / 'Data1'
        if data1.exists():
            vl_files = sorted(data1.glob('*.tt'))
            files['VL'].extend(vl_files)
            self.logger.info(f"Data1/: {len(vl_files)} train files")

        # Data2 - Autobusy
        data2 = self.komplet_dir / 'Data2'
        if data2.exists():
            bus_files = sorted(data2.glob('*.tt'))
            files['BUS'].extend(bus_files)
            self.logger.info(f"Data2/: {len(bus_files)} bus files")

        # Data3 - MHD
        data3 = self.komplet_dir / 'Data3'
        if data3.exists():
            mhd_files = sorted(data3.glob('*.tt'))
            files['MHD'].extend(mhd_files)
            self.logger.info(f"Data3/: {len(mhd_files)} MHD files")

        total = sum(len(f) for f in files.values())
        self.logger.info(f"Total: {total} .tt files found")

        return files

    def _decode_category(self, category: str, files: List[Path]):
        """Dekóduj všechny soubory v kategorii."""
        for i, tt_file in enumerate(files, 1):
            self.logger.info(f"  [{i}/{len(files)}] {tt_file.name}")

            start_time = datetime.now()
            stats = DecodingStats(
                filename=tt_file.name,
                category=category,
                success=False
            )

            try:
                # Dekóduj
                decoder = TTDecoderV2(tt_file, debug=False)
                success = decoder.decode()

                processing_time = (datetime.now() - start_time).total_seconds() * 1000

                if success:
                    # Export JSON
                    json_file = self.json_dir / category / f"{tt_file.stem}.json"
                    json_file.parent.mkdir(parents=True, exist_ok=True)
                    decoder.export_json(json_file)

                    # Statistiky
                    decoder_stats = decoder.get_stats()
                    stats.success = True
                    stats.stops = decoder_stats['stops']
                    stats.trips = decoder_stats['trips']
                    stats.edges = decoder_stats['edges']
                    stats.processing_time_ms = int(processing_time)
                    stop_offset = decoder_stats.get('best_stop_offset')
                    time_offset = decoder_stats.get('best_time_offset')
                    if stop_offset is not None or time_offset is not None:
                        stop_hex = f"0x{stop_offset:06X}" if stop_offset is not None else "n/a"
                        time_hex = f"0x{time_offset:06X}" if time_offset is not None else "n/a"
                        stats.offset_found = f"stop={stop_hex}; time={time_hex}"

                    self.logger.debug(f"    ✓ {stats.stops} stops, {stats.trips} trips, {stats.edges} edges ({processing_time:.0f}ms)")

                    self.gtfs_stats.successful += 1
                    self.gtfs_stats.categories[category] += 1

                else:
                    stats.error_message = "Decoding returned False"
                    self.logger.warning(f"    ⚠️  Decoding failed: {tt_file.name}")
                    self.gtfs_stats.failed += 1

            except Exception as e:
                stats.error_message = str(e)
                self.logger.error(f"    ❌ Error decoding {tt_file.name}: {e}")
                self.logger.debug(traceback.format_exc())
                self.gtfs_stats.failed += 1

            self.decoding_stats.append(stats)

    def _build_gtfs_feeds(self):
        """Sestav GTFS feed z dekódovaných JSON souborů."""
        for category in ['VL', 'BUS', 'MHD']:
            self.logger.info(f"\n[{category}] Building GTFS feed...")

            # Vytvoř agency
            self._create_agency(category)

            # Načti všechny JSON soubory
            json_dir = self.json_dir / category
            if not json_dir.exists():
                continue

            json_files = sorted(json_dir.glob('*.json'))
            self.logger.debug(f"  Processing {len(json_files)} JSON files")

            for json_file in json_files:
                self._add_city_to_gtfs(category, json_file)

            self.logger.info(f"  ✓ {len(self.gtfs_data[category]['stops'])} stops")
            self.logger.info(f"  ✓ {len(self.gtfs_data[category]['routes'])} routes")
            self.logger.info(f"  ✓ {len(self.gtfs_data[category]['trips'])} trips")

    def _create_agency(self, category: str):
        """Vytvoř agency záznam."""
        agency_names = {
            'VL': 'České dráhy (TT Decoded)',
            'BUS': 'Meziměstské autobusy (TT Decoded)',
            'MHD': 'Městská hromadná doprava (TT Decoded)',
        }

        self.gtfs_data[category]['agencies'].append({
            'agency_id': f'AGENCY_{category}',
            'agency_name': agency_names[category],
            'agency_url': 'https://prijimackynaskolu.cz',
            'agency_timezone': 'Europe/Prague',
            'agency_lang': 'cs'
        })

    def _add_city_to_gtfs(self, category: str, json_file: Path):
        """Přidej město do GTFS."""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        city_name = json_file.stem
        stops_list = data['stops']
        trips_data = data.get('trips', [])
        edges_data = data.get('edges', {})

        # Vytvoř zastávky
        city_stop_ids = {}
        for idx, stop_name in enumerate(stops_list):
            stop_key = (city_name, stop_name)

            if stop_key not in self.stop_mappings[category]:
                stop_id = f"{category}_{self.counters[category]['stop']}"
                self.counters[category]['stop'] += 1

                self.gtfs_data[category]['stops'].append({
                    'stop_id': stop_id,
                    'stop_name': f"{city_name}, {stop_name}",
                    'stop_lat': '',
                    'stop_lon': '',
                    'agency_id': f'AGENCY_{category}',
                })

                self.stop_mappings[category][stop_key] = stop_id

            city_stop_ids[idx] = self.stop_mappings[category][stop_key]

        # Vytvoř linku
        route_id = f"{category}_ROUTE_{self.counters[category]['route']}"
        self.counters[category]['route'] += 1

        route_types = {
            'VL': '2',    # Rail
            'BUS': '3',   # Bus
            'MHD': '3',   # Bus (MHD)
        }

        self.gtfs_data[category]['routes'].append({
            'route_id': route_id,
            'agency_id': f'AGENCY_{category}',
            'route_short_name': city_name,
            'route_long_name': f"{category} {city_name}",
            'route_type': route_types[category],
        })

        trips_added = self._add_trips_from_decoded_sequences(
            category=category,
            route_id=route_id,
            city_stop_ids=city_stop_ids,
            trips_data=trips_data,
        )

        if trips_added == 0 and edges_data:
            self.logger.debug(
                f"  [{category}/{city_name}] Falling back to edge-based trip synthesis "
                f"(decoded trips unavailable)."
            )
            self._add_trips_from_edges(category, route_id, city_stop_ids, edges_data)

    def _parse_trip_point(self, raw_point) -> Optional[Tuple[int, int]]:
        """Normalizuj bod spoje do formátu (stop_idx, minutes)."""
        try:
            if isinstance(raw_point, (list, tuple)) and len(raw_point) >= 2:
                return int(raw_point[0]), int(raw_point[1])

            if isinstance(raw_point, dict):
                stop_idx = raw_point.get('stop_idx', raw_point.get('stop'))
                minutes = raw_point.get('minutes', raw_point.get('time'))
                if stop_idx is None or minutes is None:
                    return None
                return int(stop_idx), int(minutes)
        except (TypeError, ValueError):
            return None

        return None

    def _add_trips_from_decoded_sequences(
        self,
        category: str,
        route_id: str,
        city_stop_ids: Dict[int, str],
        trips_data: List,
    ) -> int:
        """Přidej GTFS spoje z dekódovaných sekvencí zastávek+časů."""
        trips_added = 0

        for raw_trip in trips_data:
            if not isinstance(raw_trip, list):
                continue

            normalized_trip = []
            for raw_point in raw_trip:
                parsed = self._parse_trip_point(raw_point)
                if parsed is None:
                    continue

                stop_idx, minutes = parsed
                if stop_idx not in city_stop_ids:
                    continue
                if minutes < 0:
                    continue
                if normalized_trip and minutes < normalized_trip[-1][1]:
                    continue
                if normalized_trip and normalized_trip[-1][0] == stop_idx and normalized_trip[-1][1] == minutes:
                    continue

                normalized_trip.append((stop_idx, minutes))

            if len(normalized_trip) < 2:
                continue
            if len({stop_idx for stop_idx, _ in normalized_trip}) < 2:
                continue

            trip_id = f"{category}_TRIP_{self.counters[category]['trip']}"
            self.counters[category]['trip'] += 1
            trips_added += 1

            self.gtfs_data[category]['trips'].append({
                'trip_id': trip_id,
                'route_id': route_id,
                'service_id': 'WEEKDAY',
            })

            for seq, (stop_idx, minutes) in enumerate(normalized_trip, start=1):
                time_value = self._format_time(minutes)
                self.gtfs_data[category]['stop_times'].append({
                    'trip_id': trip_id,
                    'stop_id': city_stop_ids[stop_idx],
                    'stop_sequence': seq,
                    'arrival_time': time_value,
                    'departure_time': time_value,
                })

        return trips_added

    def _add_trips_from_edges(
        self,
        category: str,
        route_id: str,
        city_stop_ids: Dict[int, str],
        edges_data: Dict[str, Dict],
    ):
        """Fallback pro legacy JSON bez explicitních tripů."""
        for edge_key, edge_info in edges_data.items():
            from_idx, to_idx = map(int, edge_key.split('->'))

            if from_idx not in city_stop_ids or to_idx not in city_stop_ids:
                continue

            trip_id = f"{category}_TRIP_{self.counters[category]['trip']}"
            self.counters[category]['trip'] += 1

            self.gtfs_data[category]['trips'].append({
                'trip_id': trip_id,
                'route_id': route_id,
                'service_id': 'WEEKDAY',
            })

            start_time = 8 * 60
            self.gtfs_data[category]['stop_times'].append({
                'trip_id': trip_id,
                'stop_id': city_stop_ids[from_idx],
                'stop_sequence': 1,
                'arrival_time': self._format_time(start_time),
                'departure_time': self._format_time(start_time),
            })

            arrival_time = start_time + int(edge_info['travel_time_avg'])
            self.gtfs_data[category]['stop_times'].append({
                'trip_id': trip_id,
                'stop_id': city_stop_ids[to_idx],
                'stop_sequence': 2,
                'arrival_time': self._format_time(arrival_time),
                'departure_time': self._format_time(arrival_time),
            })

    def _format_time(self, minutes: int) -> str:
        """Formátuj minuty na HH:MM:SS."""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}:00"

    def _export_gtfs_files(self):
        """Export GTFS souborů pro každou kategorii."""
        for category in ['VL', 'BUS', 'MHD']:
            output_dir = self.output_dirs[category]
            data = self.gtfs_data[category]

            self.logger.info(f"\n[{category}] Exporting to {output_dir}/")

            # agency.txt
            self._write_csv(output_dir / 'agency.txt', data['agencies'],
                           ['agency_id', 'agency_name', 'agency_url', 'agency_timezone', 'agency_lang'])

            # stops.txt
            self._write_csv(output_dir / 'stops.txt', data['stops'],
                           ['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'agency_id'])

            # routes.txt
            self._write_csv(output_dir / 'routes.txt', data['routes'],
                           ['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type'])

            # trips.txt
            self._write_csv(output_dir / 'trips.txt', data['trips'],
                           ['trip_id', 'route_id', 'service_id'])

            # stop_times.txt
            self._write_csv(output_dir / 'stop_times.txt', data['stop_times'],
                           ['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'])

            # calendar.txt
            self._write_calendar(output_dir / 'calendar.txt')

            # Update global stats
            self.gtfs_stats.total_stops += len(data['stops'])
            self.gtfs_stats.total_routes += len(data['routes'])
            self.gtfs_stats.total_trips += len(data['trips'])
            self.gtfs_stats.total_stop_times += len(data['stop_times'])

            self.logger.info(f"  ✓ 6 GTFS files written")

    def _write_csv(self, filepath: Path, data: List[Dict], fieldnames: List[str]):
        """Zapiš CSV soubor."""
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def _write_calendar(self, filepath: Path):
        """Zapiš calendar.txt."""
        today = date.today()
        start_date = today.strftime('%Y%m%d')
        end_date = today.replace(year=today.year + 1).strftime('%Y%m%d')

        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_date', 'end_date'])
            writer.writeheader()
            writer.writerow({
                'service_id': 'WEEKDAY',
                'monday': '1',
                'tuesday': '1',
                'wednesday': '1',
                'thursday': '1',
                'friday': '1',
                'saturday': '0',
                'sunday': '0',
                'start_date': start_date,
                'end_date': end_date,
            })

    def _generate_reports(self):
        """Generuj detailní reporty."""
        report_dir = self.log_dir
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. Summary report (markdown)
        summary_file = report_dir / f'summary_{timestamp}.md'
        self._write_summary_report(summary_file)

        # 2. Detailed stats (JSON)
        stats_file = report_dir / f'stats_{timestamp}.json'
        self._write_stats_json(stats_file)

        # 3. Failed files report
        failed_file = report_dir / f'failed_{timestamp}.txt'
        self._write_failed_report(failed_file)

        self.logger.info(f"  ✓ Summary: {summary_file}")
        self.logger.info(f"  ✓ Stats: {stats_file}")
        self.logger.info(f"  ✓ Failed: {failed_file}")

    def _write_summary_report(self, filepath: Path):
        """Zapiš markdown summary."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# KOMPLET → GTFS Conversion Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Overall Statistics\n\n")
            f.write(f"- **Total files:** {self.gtfs_stats.total_files}\n")
            f.write(f"- **Successful:** {self.gtfs_stats.successful} ({100*self.gtfs_stats.successful//self.gtfs_stats.total_files if self.gtfs_stats.total_files > 0 else 0}%)\n")
            f.write(f"- **Failed:** {self.gtfs_stats.failed}\n\n")

            f.write("## GTFS Output\n\n")
            f.write(f"- **Stops:** {self.gtfs_stats.total_stops:,}\n")
            f.write(f"- **Routes:** {self.gtfs_stats.total_routes:,}\n")
            f.write(f"- **Trips:** {self.gtfs_stats.total_trips:,}\n")
            f.write(f"- **Stop times:** {self.gtfs_stats.total_stop_times:,}\n\n")

            f.write("## By Category\n\n")
            f.write("| Category | Files | Stops | Routes | Trips |\n")
            f.write("|----------|-------|-------|--------|-------|\n")

            for cat in ['VL', 'BUS', 'MHD']:
                files = self.gtfs_stats.categories[cat]
                stops = len(self.gtfs_data[cat]['stops'])
                routes = len(self.gtfs_data[cat]['routes'])
                trips = len(self.gtfs_data[cat]['trips'])

                f.write(f"| {cat} | {files} | {stops:,} | {routes:,} | {trips:,} |\n")

            # Top 10 largest files
            f.write("\n## Top 10 Cities by Stops\n\n")
            sorted_stats = sorted([s for s in self.decoding_stats if s.success],
                                key=lambda x: x.stops, reverse=True)[:10]

            f.write("| City | Category | Stops | Trips | Edges |\n")
            f.write("|------|----------|-------|-------|-------|\n")

            for stat in sorted_stats:
                f.write(f"| {stat.filename[:-3]} | {stat.category} | {stat.stops} | {stat.trips} | {stat.edges} |\n")

    def _write_stats_json(self, filepath: Path):
        """Zapiš detailní statistiky jako JSON."""
        stats_dict = {
            'summary': asdict(self.gtfs_stats),
            'decoding_details': [asdict(s) for s in self.decoding_stats],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats_dict, f, ensure_ascii=False, indent=2)

    def _write_failed_report(self, filepath: Path):
        """Zapiš seznam failed souborů."""
        failed = [s for s in self.decoding_stats if not s.success]

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Failed Files Report ({len(failed)} files)\n")
            f.write("="*80 + "\n\n")

            for stat in failed:
                f.write(f"{stat.category}/{stat.filename}\n")
                f.write(f"  Error: {stat.error_message}\n\n")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python komplet_to_gtfs.py <komplet_dir> [output_dir] [log_dir]")
        print("\nExample:")
        print("  python komplet_to_gtfs.py data/KOMPLET")
        print("  python komplet_to_gtfs.py data/KOMPLET data/GTFS_CZ")
        print("  python komplet_to_gtfs.py data/KOMPLET data/GTFS_CZ logs")
        sys.exit(1)

    komplet_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('data/GTFS_CZ')
    log_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('logs')

    if not komplet_dir.exists():
        print(f"❌ Directory does not exist: {komplet_dir}")
        sys.exit(1)

    converter = KompletToGTFS(komplet_dir, output_dir, log_dir=log_dir)
    success = converter.convert()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
