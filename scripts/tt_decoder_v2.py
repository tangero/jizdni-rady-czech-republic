#!/usr/bin/env python3
"""
CHAPS .tt Binary Format Decoder v2
Vylepšená verze s automatickým hledáním správné sekce časových záznamů.
"""

import struct
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import json


class TTDecoderV2:
    SERVICE_TEXT_KEYWORDS = (
        'arbeitstage',
        'working day',
        'monday',
        'tuesday',
        'wednesday',
        'thursday',
        'friday',
        'saturday',
        'sunday',
        'jede',
        'premáva',
        'montag',
        'dienstag',
        'mittwoch',
        'donnerstag',
        'freitag',
        'samstag',
        'sonntag',
        'pondělí',
        'úterý',
        'středu',
        'čtvrtek',
        'pátek',
        'sobotu',
        'neděli',
        'pracovních dnech',
        'pondelok',
        'utorok',
        'stredu',
        'štvrtok',
        'piatok',
        'nedeľu',
        'pracovných dňoch',
        'jede v',
        'státem uznané svátky',
        'štátom uznané sviatky',
        'platzreservierung',
        'místenku',
        'rezervace',
        'rezervácia',
        'bezbariéro',
        'občerstven',
        'na znamení',
        'na znamenie',
        'integrovanej dopravy',
        'svátek',
        'sviat',
    )

    BAD_STOP_KEYWORDS = (
        'copyright',
        'http://',
        'https://',
        'internet',
        'pid.tt',
    )

    STOP_NOTE_KEYWORDS = (
        '{l}',
        '¤¤',
        'spoj ',
        'linka ',
        'jede jen',
        'tarif',
        'přeprav',
        'preprav',
        'ceník',
        'cenník',
        'informace',
        'vozidlech',
        'zvýhodně',
        'zvyhodne',
        'bankovní',
        'bankovu',
        'na lince platí',
    )

    def __init__(self, filepath: Path, debug=False):
        self.filepath = filepath
        self.data = filepath.read_bytes()
        self.stops: List[str] = []
        self.p_records: List[str] = []
        self.trips: List[List[Tuple[int, int]]] = []
        self.edges: Dict[Tuple[int, int], List[int]] = {}
        self.best_stop_offset: Optional[int] = None
        self.best_time_offset: Optional[int] = None
        self.stop_quality_score: float = 0.0
        if debug:
            self._debug = True

    def decode(self) -> bool:
        """Hlavní dekódovací funkce."""
        try:
            if not self._verify_header():
                return False

            if not self._find_stops():
                return False

            self._find_p_records()

            if not self._decode_time_records_smart():
                return False

            self._filter_stops()

            self._extract_edges()

            return True

        except Exception as e:
            if hasattr(self, '_debug'):
                print(f"❌ {self.filepath.name}: Chyba: {e}")
            return False

    def _verify_header(self) -> bool:
        """Ověř TT header (66 bytes)."""
        if len(self.data) < 66:
            return False
        header_str = self.data[0:60].decode('cp1250', errors='ignore')
        return 'TT' in header_str and 'TimeTable' in header_str and 'CHAPS' in header_str

    def _is_likely_service_text(self, name: str) -> bool:
        lowered = name.lower()
        return any(keyword in lowered for keyword in self.SERVICE_TEXT_KEYWORDS)

    def _extract_stop_candidate(self, offset: int) -> Optional[List[str]]:
        """Pokus se extrahovat kandidátní seznam zastávek z daného offsetu."""
        if offset + 8 > len(self.data):
            return None

        total_bytes = struct.unpack('<I', self.data[offset:offset+4])[0]
        item_count = struct.unpack('<I', self.data[offset+4:offset+8])[0]

        if total_bytes != item_count * 4:
            return None

        if item_count < 2 or item_count > 20_000:
            return None

        offsets_start = offset + 8
        offsets_end = offsets_start + total_bytes
        if offsets_end + 8 > len(self.data):
            return None

        offsets = []
        prev_off = -1
        for i in range(item_count):
            off = struct.unpack('<I', self.data[offsets_start + i*4:offsets_start + i*4 + 4])[0]
            if off < prev_off:
                return None
            offsets.append(off)
            prev_off = off

        blob_start = offsets_end
        blob_size_1 = struct.unpack('<I', self.data[blob_start:blob_start+4])[0]
        blob_size_2 = struct.unpack('<I', self.data[blob_start+4:blob_start+8])[0]

        if blob_size_1 != blob_size_2 or blob_size_1 <= 0:
            return None

        if offsets[-1] != blob_size_1:
            return None

        blob_data_start = blob_start + 8
        blob_data_end = blob_data_start + blob_size_1
        if blob_data_end > len(self.data):
            return None

        blob_data = self.data[blob_data_start:blob_data_end]

        stop_names = []
        for i in range(item_count - 1):
            start_idx = offsets[i]
            end_idx = offsets[i + 1]

            if end_idx < start_idx or end_idx > blob_size_1:
                return None

            name_bytes = blob_data[start_idx:end_idx]
            name = name_bytes.decode('cp1250', errors='replace').rstrip('\x00').strip()
            stop_names.append(name)

        return stop_names

    def _score_stop_candidate(self, stop_names: List[str]) -> float:
        """Spočítej kvalitu kandidátního seznamu zastávek."""
        if len(stop_names) < 10:
            return float('-inf')

        lowered = [name.lower() for name in stop_names]
        bad_hits = sum(
            1
            for name in lowered
            if any(keyword in name for keyword in self.BAD_STOP_KEYWORDS)
        )
        service_hits = sum(1 for name in stop_names if self._is_likely_service_text(name))
        note_hits = sum(
            1
            for name in lowered
            if any(keyword in name for keyword in self.STOP_NOTE_KEYWORDS)
        )
        empty_count = sum(1 for name in stop_names if not name)
        short_count = sum(1 for name in stop_names if len(name.strip()) <= 1)
        very_long_count = sum(1 for name in stop_names if len(name) > 45)
        markup_count = sum(1 for name in stop_names if '{' in name or '}' in name or '¤' in name or '|' in name)

        unique_ratio = len(set(stop_names)) / len(stop_names)
        avg_len = sum(len(name) for name in stop_names) / len(stop_names)

        total_chars = sum(len(name) for name in stop_names) or 1
        alpha_chars = sum(1 for name in stop_names for ch in name if ch.isalpha())
        alpha_ratio = alpha_chars / total_chars

        score = float(len(stop_names))
        score += min(avg_len, 30.0) * 2.0
        score += unique_ratio * 35.0
        score -= bad_hits * 15.0
        score -= service_hits * 10.0
        score -= note_hits * 10.0
        score -= empty_count * 20.0
        score -= short_count * 4.0
        score -= very_long_count * 6.0
        score -= markup_count * 15.0

        if service_hits / len(stop_names) > 0.25:
            score -= 80.0
        if note_hits / len(stop_names) > 0.2:
            score -= 80.0
        if alpha_ratio < 0.45:
            score -= 30.0
        if unique_ratio < 0.6:
            score -= 25.0
        if very_long_count / len(stop_names) > 0.2:
            score -= 50.0

        return score

    def _find_stops(self) -> bool:
        """Najdi nejlepší kandidátní tabulku zastávek."""
        file_size = len(self.data)
        if file_size < 1_000_000:  # < 1 MB
            search_limit = file_size
        elif file_size < 10_000_000:  # < 10 MB
            search_limit = 1_000_000  # 1 MB
        elif file_size < 40_000_000:  # < 40 MB
            search_limit = 4_000_000  # 4 MB
        else:  # >= 40 MB
            search_limit = 8_000_000  # 8 MB

        best_names: Optional[List[str]] = None
        best_score = float('-inf')
        best_offset: Optional[int] = None
        candidates_found = 0

        max_offset = min(0x40 + search_limit, len(self.data) - 8)
        for alignment in range(4):
            for offset in range(0x40 + alignment, max_offset, 4):
                try:
                    stop_names = self._extract_stop_candidate(offset)
                    if not stop_names:
                        continue

                    candidates_found += 1
                    score = self._score_stop_candidate(stop_names)

                    if score > best_score:
                        best_score = score
                        best_names = stop_names
                        best_offset = offset
                except Exception:
                    continue

        if best_names and len(best_names) >= 10 and best_score >= 20.0:
            self.stops = best_names
            self.best_stop_offset = best_offset
            self.stop_quality_score = best_score
            if hasattr(self, '_debug'):
                print(
                    f"  DEBUG: Stop candidates={candidates_found}, selected offset=0x{best_offset:06X}, "
                    f"stops={len(best_names)}, score={best_score:.1f}"
                )
            return True

        if best_names and len(best_names) >= 10:
            # Fallback: vrať alespoň nejlepší dostupný kandidát i při nízkém skóre.
            self.stops = best_names
            self.best_stop_offset = best_offset
            self.stop_quality_score = best_score
            if hasattr(self, '_debug'):
                print(
                    f"  DEBUG: Low-quality stop fallback used at offset=0x{best_offset:06X}, "
                    f"stops={len(best_names)}, score={best_score:.1f}"
                )
            return True

        return False

    def _find_p_records(self):
        """Najdi P-records."""
        separator = b'\xa4\xa4'
        start = 0x1000
        end = min(start + 50000, len(self.data))

        records = []
        i = start
        while i < end - 100:
            if self.data[i:i+1] == b'P':
                record_end = i + 1
                while record_end < end and self.data[record_end:record_end+2] != separator:
                    record_end += 1

                record_bytes = self.data[i:record_end]
                try:
                    record_str = record_bytes.decode('cp1250', errors='ignore')
                    if record_str.startswith('P'):
                        records.append(record_str)
                except:
                    pass

                i = record_end + 2
            else:
                i += 1

        self.p_records = records[:50]

    def _find_time_sections(self) -> List[Dict]:
        """Najdi kandidátní sekce časových záznamů podle rychlého skenu."""
        sections_found = []

        file_size = len(self.data)
        if file_size < 1_000_000:  # < 1 MB
            scan_limit = file_size
        elif file_size < 10_000_000:  # < 10 MB
            scan_limit = 5_000_000  # 5 MB
        else:  # >= 10 MB
            scan_limit = 20_000_000  # 20 MB

        for start in range(0x100, min(len(self.data), scan_limit), 0x400):
            for alignment in range(4):
                offset = start + alignment

                valid_count = 0
                unique_times = set()
                unique_stops = set()

                for i in range(30):
                    pos = offset + i * 4
                    if pos + 3 >= len(self.data):
                        break

                    try:
                        val = struct.unpack('<I', self.data[pos:pos+4])[0]
                        byte1 = (val >> 8) & 0xFF
                        minutes = (val >> 16) & 0x7FFF
                        stop_idx = val & 0xFF

                        if byte1 == 0x00 and minutes <= 1440:
                            valid_count += 1
                            unique_times.add(minutes)
                            unique_stops.add(stop_idx)
                    except Exception:
                        break

                if valid_count >= 10 and len(unique_times) > 5 and len(unique_stops) > 3:
                    scan_score = valid_count * len(unique_times) * len(unique_stops)
                    sections_found.append({
                        'offset': offset,
                        'scan_score': scan_score,
                        'valid': valid_count,
                        'times': len(unique_times),
                        'stops': len(unique_stops),
                    })

        sections_found.sort(key=lambda x: x['scan_score'], reverse=True)
        return sections_found

    def _score_trips(self, trips: List[List[Tuple[int, int]]]) -> float:
        if not trips:
            return float('-inf')

        valid_trips = [trip for trip in trips if len({stop for stop, _ in trip}) >= 2]
        lengths = [len(trip) for trip in valid_trips if trip]
        if not lengths:
            return float('-inf')

        total_records = sum(lengths)
        unique_stops = len({stop for trip in valid_trips for stop, _ in trip})
        avg_len = total_records / len(lengths)
        long_trips = sum(1 for length in lengths if length >= 6)

        score = float(total_records)
        score += len(valid_trips) * 5.0
        score += unique_stops * 2.0
        score += avg_len * 3.0
        score += long_trips * 8.0

        if avg_len < 2.2:
            score -= 120.0
        if unique_stops < 4:
            score -= 80.0

        return score

    def _decode_time_records_smart(self) -> bool:
        """Dekóduj časové záznamy z nejlepší kandidátní sekce."""
        sections = self._find_time_sections()
        if not sections:
            if hasattr(self, '_debug'):
                print("  DEBUG: Nenalezena žádná dobrá sekce časových záznamů")
            return False

        best_trips: Optional[List[List[Tuple[int, int]]]] = None
        best_offset: Optional[int] = None
        best_score = float('-inf')

        # Projdi pouze nejlepší kandidáty, aby to zůstalo rychlé.
        for section in sections[:16]:
            offset = section['offset']
            trips = self._decode_from_offset(offset)
            if not trips:
                continue

            # Předběžný filtr kvality
            if len(trips) < 2 and not (len(trips) == 1 and len(trips[0]) >= 10):
                continue

            trip_score = self._score_trips(trips)
            if trip_score == float('-inf'):
                continue
            combined_score = trip_score + section['scan_score'] / 1000.0

            if combined_score > best_score:
                best_score = combined_score
                best_trips = trips
                best_offset = offset

        if best_trips is None:
            return False

        self.trips = best_trips
        self.best_time_offset = best_offset

        if hasattr(self, '_debug'):
            print(
                f"  DEBUG: Time sections={len(sections)}, selected offset=0x{best_offset:06X}, "
                f"trips={len(best_trips)}, score={best_score:.1f}"
            )

        return True

    def _decode_from_offset(self, start_offset: int) -> List[List[Tuple[int, int]]]:
        """Dekóduj časové záznamy od daného offsetu."""
        trips = []
        current_trip = []
        prev_minutes = None
        same_minute_streak = 0

        end = min(start_offset + 50000, len(self.data))

        for offset in range(start_offset, end - 3, 4):
            try:
                val = struct.unpack('<I', self.data[offset:offset+4])[0]

                byte1 = (val >> 8) & 0xFF

                if byte1 != 0x00:
                    continue

                minutes = (val >> 16) & 0x7FFF
                stop_idx = val & 0xFF

                if minutes > 1440:
                    continue

                if len(self.stops) == 0 or stop_idx >= len(self.stops):
                    continue

                # Detekce hranice spoje (pokles času)
                if prev_minutes is not None and minutes < prev_minutes:
                    if len(current_trip) >= 2:
                        trips.append(current_trip)
                    current_trip = []
                    same_minute_streak = 0

                # Obří časové skoky obvykle značí přechod mezi různými bloky.
                if prev_minutes is not None and minutes - prev_minutes > 240:
                    if len(current_trip) >= 2:
                        trips.append(current_trip)
                    current_trip = []
                    same_minute_streak = 0

                # Odfiltruj bezprostřední duplikáty z binárního šumu.
                if current_trip and current_trip[-1][0] == stop_idx and current_trip[-1][1] == minutes:
                    prev_minutes = minutes
                    continue

                if prev_minutes is not None and minutes == prev_minutes:
                    same_minute_streak += 1
                    # Více než několik změn zastávky ve stejné minutě bývá šum.
                    if same_minute_streak > 3:
                        prev_minutes = minutes
                        continue
                else:
                    same_minute_streak = 1

                current_trip.append((stop_idx, minutes))
                prev_minutes = minutes

            except Exception:
                continue

        if len(current_trip) >= 2:
            trips.append(current_trip)

        return trips

    def _filter_stops(self):
        """Odstraň nesmyslné zastávky (POI, legendy, CHAPS kódy) a přemapuj indexy."""
        if not self.stops or not self.trips:
            return

        # 1. Zjisti, které stop indexy jsou referencovány v trips
        referenced_indices: set[int] = set()
        for trip in self.trips:
            for stop_idx, _ in trip:
                referenced_indices.add(stop_idx)

        # 2. Pattern-based filtering
        POI_KEYWORDS = (
            'unicredit', 'spořitelna', 'sporitelna', 'pobočka', 'pobocka',
            'a.s.', 'bankomat', 'banka,', 'bank,',
        )

        def is_bad_stop(name: str) -> bool:
            if not name or not name.strip():
                return True
            if name.startswith('¤¤'):
                return True
            if '{L}' in name or '{l}' in name:
                return True
            if name.startswith('*') and len(name) <= 6 and name[1:].isalpha():
                return True
            lowered = name.lower()
            if any(kw in lowered for kw in self.SERVICE_TEXT_KEYWORDS):
                return True
            if any(kw in lowered for kw in POI_KEYWORDS):
                return True
            return False

        # 3. Vytvoř nový seznam zastávek a mapping
        old_to_new: dict[int, int] = {}
        new_stops: list[str] = []

        for old_idx, name in enumerate(self.stops):
            if old_idx not in referenced_indices:
                continue
            if is_bad_stop(name):
                continue
            old_to_new[old_idx] = len(new_stops)
            new_stops.append(name)

        if not new_stops:
            return

        # 4. Přemapuj trips
        new_trips: list[list[tuple[int, int]]] = []
        for trip in self.trips:
            new_trip = []
            for stop_idx, minutes in trip:
                if stop_idx in old_to_new:
                    new_trip.append((old_to_new[stop_idx], minutes))
            if len(new_trip) >= 2:
                new_trips.append(new_trip)

        # 5. Přemapuj edges
        new_edges: dict[tuple[int, int], list[int]] = {}
        for (from_idx, to_idx), times in self.edges.items():
            if from_idx in old_to_new and to_idx in old_to_new:
                new_key = (old_to_new[from_idx], old_to_new[to_idx])
                new_edges[new_key] = times

        if hasattr(self, '_debug'):
            removed = len(self.stops) - len(new_stops)
            if removed > 0:
                print(f"  DEBUG: Filtered stops: {len(self.stops)} → {len(new_stops)} (removed {removed})")

        self.stops = new_stops
        self.trips = new_trips
        self.edges = new_edges

    def _extract_edges(self):
        """Extrahuj hrany cestovního grafu."""
        for trip in self.trips:
            for i in range(len(trip) - 1):
                stop_from, time_from = trip[i]
                stop_to, time_to = trip[i + 1]

                travel_time = time_to - time_from

                if stop_from == stop_to:
                    continue

                if travel_time < 1 or travel_time > 60:
                    continue

                edge = (stop_from, stop_to)
                if edge not in self.edges:
                    self.edges[edge] = []
                self.edges[edge].append(travel_time)

    def get_stats(self) -> Dict:
        """Vrať statistiky."""
        unique_edges = len(self.edges)
        total_times = sum(len(times) for times in self.edges.values())

        return {
            'stops': len(self.stops),
            'trips': len(self.trips),
            'edges': unique_edges,
            'total_travel_times': total_times,
            'p_records': len(self.p_records),
            'best_stop_offset': self.best_stop_offset,
            'best_time_offset': self.best_time_offset,
            'stop_quality_score': round(self.stop_quality_score, 2),
        }

    def export_json(self, output_path: Path):
        """Export do JSON."""
        edges_avg = {}
        for (from_idx, to_idx), times in self.edges.items():
            avg_time = sum(times) / len(times)
            edges_avg[f"{from_idx}->{to_idx}"] = {
                'from_stop': self.stops[from_idx] if from_idx < len(self.stops) else f"Stop#{from_idx}",
                'to_stop': self.stops[to_idx] if to_idx < len(self.stops) else f"Stop#{to_idx}",
                'travel_time_avg': round(avg_time, 1),
                'travel_time_min': min(times),
                'travel_time_max': max(times),
                'samples': len(times)
            }

        data = {
            'source_file': self.filepath.name,
            'stops': self.stops,
            'trips': self.trips,
            'stats': self.get_stats(),
            'edges': edges_avg
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def batch_decode(data_dir: Path, output_dir: Path):
    """Dávkové dekódování."""
    tt_files = sorted(data_dir.glob('*.tt'))

    if not tt_files:
        print(f"❌ Žádné .tt soubory v {data_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    total_stops = 0
    total_trips = 0
    total_edges = 0

    print(f"🔍 Dekóduji {len(tt_files)} souborů z {data_dir}...\n")

    for tt_file in tt_files:
        decoder = TTDecoderV2(tt_file)

        if decoder.decode():
            stats = decoder.get_stats()

            json_file = output_dir / f"{tt_file.stem}.json"
            decoder.export_json(json_file)

            print(f"✓ {tt_file.name:30s} {stats['stops']:3d} zastávek, {stats['trips']:3d} spojů, {stats['edges']:4d} hran")

            success_count += 1
            total_stops += stats['stops']
            total_trips += stats['trips']
            total_edges += stats['edges']

    print(f"\n{'='*80}")
    print(f"SUCCESS: {success_count}/{len(tt_files)} ({100*success_count//len(tt_files)}%)")
    print(f"  {total_stops:,} zastávek")
    print(f"  {total_trips:,} spojů")
    print(f"  {total_edges:,} unikátních hran cestovních časů")
    print(f"\n💾 Exportováno do: {output_dir}/")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tt_decoder_v2.py <file.tt>              # Dekóduj jeden soubor")
        print("  python tt_decoder_v2.py --batch <data_dir>     # Dekóduj celou složku")
        sys.exit(1)

    if sys.argv[1] == '--batch':
        if len(sys.argv) < 3:
            print("❌ Chybí cesta ke složce")
            sys.exit(1)

        data_dir = Path(sys.argv[2])
        output_dir = Path('data/decoded_tt_v2')
        batch_decode(data_dir, output_dir)

    else:
        tt_file = Path(sys.argv[1])

        if not tt_file.exists():
            print(f"❌ Soubor neexistuje: {tt_file}")
            sys.exit(1)

        decoder = TTDecoderV2(tt_file, debug=True)

        if decoder.decode():
            stats = decoder.get_stats()

            print(f"\n✓ Dekódováno: {tt_file.name}")
            print(f"  Zastávky: {stats['stops']}")
            print(f"  Spoje: {stats['trips']}")
            print(f"  Hrany: {stats['edges']}")

            output_dir = Path('data/decoded_tt_v2_single')
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{tt_file.stem}.json"
            decoder.export_json(output_file)
            print(f"\n💾 Exportováno: {output_file}")
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
