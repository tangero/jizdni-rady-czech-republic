#!/usr/bin/env python3
"""
Konverze IDOS .tt souborů (KOMPLET.ZIP) do GTFS formátu.

Skript zpracovává soubory IDOS ve formátu .tt, které jsou publikovány
v archivu KOMPLET.ZIP ke stažení na:
    https://www.chaps.cz/cs/download/idos#kotvatt

Pipeline:
1. Dekóduje .tt binární soubory (tt_decoder_v2.py)
2. Konvertuje dekódovaná data do GTFS (komplet_to_gtfs.py)
3. Sloučí kategorie VL/BUS/MHD do jednoho GTFS zdroje
4. Volitelně spustí integraci se všemi GTFS zdroji

Prerekvizity:
    - Python 3.9+
    - Žádné externí závislosti (pouze stdlib)
    - Stažený a rozbalený KOMPLET.ZIP z https://www.chaps.cz/cs/download/idos#kotvatt

Použití:
    # 1. Stáhni KOMPLET.ZIP z https://www.chaps.cz/cs/download/idos#kotvatt
    # 2. Rozbal ZIP archiv
    # 3. Spusť konverzi:
    python scripts/convert_tt_to_gtfs.py /cesta/ke/KOMPLET

    # Konverze + integrace všech zdrojů
    python scripts/convert_tt_to_gtfs.py /cesta/ke/KOMPLET --integrate

    # Vlastní výstupní adresář
    python scripts/convert_tt_to_gtfs.py /cesta/ke/KOMPLET --output-dir data/moje_gtfs

Aktualizace dat:
    1. Stáhni nový KOMPLET.ZIP z https://www.chaps.cz/cs/download/idos#kotvatt
       - Archiv je aktualizován při každé změně jízdních řádů
       - Obsahuje Data1/ (vlaky), Data2/ (autobusy), Data3/ (MHD)
    2. Rozbal KOMPLET.ZIP kamkoliv na disk
    3. Spusť: python scripts/convert_tt_to_gtfs.py /cesta/ke/KOMPLET --integrate
    4. Zkontroluj výstup v data/mhd/, data/regional/, data/merged/
    5. Commitni změny

Struktura KOMPLET.ZIP:
    KOMPLET/
    ├── Data1/          # Vlakové .tt soubory (VL)
    │   ├── Vlak26C.tt
    │   └── ...
    ├── Data2/          # Autobusové .tt soubory (BUS)
    │   ├── Bus26C.tt
    │   └── ...
    └── Data3/          # Městská MHD .tt soubory (MHD)
        ├── Praha.tt
        ├── Brno.tt
        └── ...

Co je .tt formát:
    Proprietární binární formát firmy CHAPS spol. s r.o. používaný
    systémem IDOS pro distribuci jízdních řádů v ČR a SR. Obsahuje
    zastávky, časy odjezdů/příjezdů, hrany cestovního grafu a metadata
    linek. Dekodér (tt_decoder_v2.py) extrahuje data heuristicky — hledá
    nejlepší kandidátní tabulku zastávek a časových záznamů v binárním
    blobu a filtruje nesmyslné záznamy (POI, servisní texty, CHAPS kódy).
"""

import argparse
import csv
import shutil
import sys
from pathlib import Path

# Lokální importy ze stejného adresáře
sys.path.insert(0, str(Path(__file__).parent))
from komplet_to_gtfs import KompletToGTFS


PROJECT_DIR = Path(__file__).resolve().parent.parent


def run_conversion(komplet_dir: Path, output_dir: Path, log_dir: Path) -> bool:
    """Spusť KOMPLET → GTFS konverzi."""
    print("=" * 80)
    print("FÁZE 1: KONVERZE KOMPLET → GTFS")
    print("=" * 80)
    print(f"  Vstup:  {komplet_dir}")
    print(f"  Výstup: {output_dir}")
    print(f"  Logy:   {log_dir}")
    print()

    converter = KompletToGTFS(komplet_dir, output_dir, log_dir=log_dir)
    return converter.convert()


def merge_categories(gtfs_dir: Path, target_dir: Path) -> None:
    """Slouč VL, BUS a MHD GTFS do jednoho adresáře pro integraci."""
    print()
    print("=" * 80)
    print("FÁZE 2: SLOUČENÍ KATEGORIÍ → tt_source/ALL")
    print("=" * 80)

    target_dir.mkdir(parents=True, exist_ok=True)

    categories = ["MHD", "VL", "BUS"]
    gtfs_files = [
        "agency.txt", "calendar.txt", "routes.txt",
        "stops.txt", "trips.txt", "stop_times.txt",
    ]

    first = True
    for cat in categories:
        cat_dir = gtfs_dir / cat
        if not cat_dir.exists():
            print(f"  Kategorie {cat} neexistuje, přeskakuji")
            continue

        print(f"  {'Kopíruji' if first else 'Přidávám'} {cat}...")

        for fname in gtfs_files:
            src = cat_dir / fname
            dst = target_dir / fname

            if not src.exists():
                continue

            if first:
                shutil.copy2(src, dst)
            else:
                with open(src, "r", encoding="utf-8") as f_in:
                    reader = csv.reader(f_in)
                    next(reader)  # skip header
                    with open(dst, "a", encoding="utf-8", newline="") as f_out:
                        writer = csv.writer(f_out)
                        for row in reader:
                            writer.writerow(row)

        first = False

    print()
    for fname in gtfs_files:
        fpath = target_dir / fname
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f) - 1
            print(f"  {fname}: {count:,} záznamů")


def run_integration() -> bool:
    """Spusť integraci všech GTFS zdrojů."""
    print()
    print("=" * 80)
    print("FÁZE 3: INTEGRACE VŠECH GTFS ZDROJŮ")
    print("=" * 80)

    integration_script = PROJECT_DIR / "scripts" / "integrate_all_data_fast.py"
    if not integration_script.exists():
        print(f"Integrační skript nenalezen: {integration_script}")
        return False

    import subprocess
    result = subprocess.run(
        [sys.executable, str(integration_script)],
        cwd=str(PROJECT_DIR),
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Konverze CHAPS .tt souborů (KOMPLET) do GTFS formátu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady:
  %(prog)s /cesta/ke/KOMPLET
  %(prog)s /cesta/ke/KOMPLET --integrate
  %(prog)s /cesta/ke/KOMPLET --output-dir data/moje_gtfs
        """,
    )
    parser.add_argument(
        "komplet_dir", type=Path,
        help="Cesta ke KOMPLET adresáři obsahujícímu Data1/, Data2/, Data3/",
    )
    parser.add_argument(
        "--integrate", action="store_true",
        help="Po konverzi spustit integraci se všemi GTFS zdroji (PID, GTFS_CR atd.)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Výstupní adresář pro GTFS soubory (default: data/gtfs_output)",
    )

    args = parser.parse_args()

    komplet_dir = args.komplet_dir.resolve()
    if not komplet_dir.exists():
        print(f"KOMPLET adresář neexistuje: {komplet_dir}")
        sys.exit(1)

    # Zkontroluj Data1/Data2/Data3
    has_data = any((komplet_dir / d).exists() for d in ["Data1", "Data2", "Data3"])
    if not has_data:
        print(f"KOMPLET adresář neobsahuje Data1/, Data2/ ani Data3/: {komplet_dir}")
        sys.exit(1)

    gtfs_output = (args.output_dir or PROJECT_DIR / "data" / "gtfs_output").resolve()
    log_dir = PROJECT_DIR / "logs"
    tt_source_dir = PROJECT_DIR / "data" / "tt_source" / "ALL"

    # 1. Konverze TT → GTFS
    if not run_conversion(komplet_dir, gtfs_output, log_dir):
        print("\nKonverze selhala!")
        sys.exit(1)

    # 2. Sloučení VL+BUS+MHD
    merge_categories(gtfs_output, tt_source_dir)

    # 3. Volitelná integrace
    if args.integrate:
        if not run_integration():
            print("\nIntegrace selhala!")
            sys.exit(1)

    print()
    print("=" * 80)
    print("HOTOVO")
    print("=" * 80)
    print(f"  GTFS (po kategoriích): {gtfs_output}")
    print(f"  GTFS (sloučený):       {tt_source_dir}")
    if args.integrate:
        print(f"  Integrováno do:        {PROJECT_DIR / 'data'}")
    else:
        print()
        print("  Pro integraci se všemi zdroji spusť znovu s --integrate")


if __name__ == "__main__":
    main()
