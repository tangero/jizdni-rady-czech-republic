# Průvodce použitím

Tento průvodce ukazuje, jak pracovat s GTFS daty pro Českou republiku.

## Rychlý start

### 1. Načtení dat

```python
import csv
from pathlib import Path

# Cesta k GTFS datům
gtfs_dir = Path('data/mhd')

# Načtení zastávek
stops = []
with open(gtfs_dir / 'stops.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    stops = list(reader)

print(f"Celkem zastávek: {len(stops)}")
print(f"První zastávka: {stops[0]['stop_name']}")
```

### 2. Analýza linek

```python
# Načtení linek
routes = []
with open(gtfs_dir / 'routes.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    routes = list(reader)

# Seskupení podle typu
from collections import defaultdict

routes_by_type = defaultdict(list)
for route in routes:
    route_type = route['route_type']
    routes_by_type[route_type].append(route)

# GTFS route_type: 3 = autobus, 0 = tramvaj, 1 = metro, 2 = vlak
type_names = {'0': 'Tramvaj', '1': 'Metro', '2': 'Vlak', '3': 'Autobus'}

for type_id, routes_list in routes_by_type.items():
    type_name = type_names.get(type_id, f'Typ {type_id}')
    print(f"{type_name}: {len(routes_list)} linek")
```

### 3. Vyhledání spojů

```python
# Načtení spojů pro konkrétní linku
trips = []
with open(gtfs_dir / 'trips.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for trip in reader:
        if trip['route_id'] == 'MHD_ROUTE_0':  # Konkrétní linka
            trips.append(trip)

print(f"Nalezeno {len(trips)} spojů na této lince")
```

## Pokročilé použití

### Výpočet dojezdové doby

```python
def calculate_travel_time(trip_id):
    """Vypočítá celkovou dobu spoje."""
    stop_times = []

    with open(gtfs_dir / 'stop_times.txt', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for st in reader:
            if st['trip_id'] == trip_id:
                stop_times.append(st)

    if not stop_times:
        return None

    # Seřaď podle stop_sequence
    stop_times.sort(key=lambda x: int(x['stop_sequence']))

    # První a poslední čas
    start_time = stop_times[0]['departure_time']
    end_time = stop_times[-1]['arrival_time']

    # Převod na minuty
    def time_to_minutes(time_str):
        h, m, s = map(int, time_str.split(':'))
        return h * 60 + m

    start_mins = time_to_minutes(start_time)
    end_mins = time_to_minutes(end_time)

    return end_mins - start_mins

# Příklad
travel_time = calculate_travel_time('MHD_TRIP_0')
print(f"Doba jízdy: {travel_time} minut")
```

### Vytvoření grafu spojení

```python
from collections import defaultdict

def build_transit_graph():
    """Vytvoří graf zastávek a jejich spojení."""
    graph = defaultdict(list)

    with open(gtfs_dir / 'stop_times.txt', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        stop_times = list(reader)

    # Seskupit podle trip_id
    trips = defaultdict(list)
    for st in stop_times:
        trips[st['trip_id']].append(st)

    # Vytvoř hrany mezi po sobě jdoucími zastávkami
    for trip_id, times in trips.items():
        times.sort(key=lambda x: int(x['stop_sequence']))

        for i in range(len(times) - 1):
            from_stop = times[i]['stop_id']
            to_stop = times[i + 1]['stop_id']

            # Doba jízdy
            from_time = time_to_minutes(times[i]['departure_time'])
            to_time = time_to_minutes(times[i + 1]['arrival_time'])
            duration = to_time - from_time

            graph[from_stop].append({
                'to': to_stop,
                'duration': duration,
                'trip_id': trip_id
            })

    return graph

def time_to_minutes(time_str):
    h, m, s = map(int, time_str.split(':'))
    return h * 60 + m

# Vytvoř graf
transit_graph = build_transit_graph()
print(f"Graf obsahuje {len(transit_graph)} zastávek")
```

### Dijkstra algoritmus pro nalezení nejkratší cesty

```python
import heapq

def dijkstra(graph, start_stop, end_stop):
    """Najde nejkratší cestu mezi dvěma zastávkami."""
    # Prioritní fronta: (čas, zastávka, cesta)
    queue = [(0, start_stop, [])]
    visited = set()

    while queue:
        time, current, path = heapq.heappop(queue)

        if current in visited:
            continue

        visited.add(current)
        path = path + [current]

        if current == end_stop:
            return time, path

        # Projdi sousedy
        for edge in graph.get(current, []):
            if edge['to'] not in visited:
                new_time = time + edge['duration']
                heapq.heappush(queue, (new_time, edge['to'], path))

    return None, []  # Cesta nenalezena

# Příklad
graph = build_transit_graph()
time, path = dijkstra(graph, 'MHD_STOP_0', 'MHD_STOP_10')

if path:
    print(f"Cesta nalezena: {len(path)} zastávek, {time} minut")
    print(f"Trasa: {' → '.join(path)}")
else:
    print("Cesta nenalezena")
```

## Import do databáze

### PostgreSQL

```sql
-- Vytvoř tabulky
CREATE TABLE agencies (
    agency_id TEXT PRIMARY KEY,
    agency_name TEXT NOT NULL,
    agency_url TEXT,
    agency_timezone TEXT,
    agency_lang TEXT
);

CREATE TABLE stops (
    stop_id TEXT PRIMARY KEY,
    stop_name TEXT NOT NULL,
    stop_lat NUMERIC,
    stop_lon NUMERIC
);

CREATE TABLE routes (
    route_id TEXT PRIMARY KEY,
    agency_id TEXT REFERENCES agencies(agency_id),
    route_short_name TEXT,
    route_long_name TEXT,
    route_type INTEGER
);

CREATE TABLE trips (
    trip_id TEXT PRIMARY KEY,
    route_id TEXT REFERENCES routes(route_id),
    service_id TEXT
);

CREATE TABLE stop_times (
    trip_id TEXT REFERENCES trips(trip_id),
    stop_id TEXT REFERENCES stops(stop_id),
    stop_sequence INTEGER,
    arrival_time TEXT,
    departure_time TEXT,
    PRIMARY KEY (trip_id, stop_sequence)
);

-- Import dat
\copy agencies FROM 'data/mhd/agency.txt' CSV HEADER;
\copy stops FROM 'data/mhd/stops.txt' CSV HEADER;
\copy routes FROM 'data/mhd/routes.txt' CSV HEADER;
\copy trips FROM 'data/mhd/trips.txt' CSV HEADER;
\copy stop_times FROM 'data/mhd/stop_times.txt' CSV HEADER;
```

### SQLite

```python
import sqlite3
import csv

def import_gtfs_to_sqlite(gtfs_dir, db_path):
    """Import GTFS dat do SQLite databáze."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Vytvoř tabulky
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stops (
            stop_id TEXT PRIMARY KEY,
            stop_name TEXT,
            stop_lat REAL,
            stop_lon REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routes (
            route_id TEXT PRIMARY KEY,
            agency_id TEXT,
            route_short_name TEXT,
            route_long_name TEXT,
            route_type INTEGER
        )
    ''')

    # Import zastávek
    with open(f'{gtfs_dir}/stops.txt', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute('''
                INSERT INTO stops VALUES (?, ?, ?, ?)
            ''', (row['stop_id'], row['stop_name'],
                  float(row['stop_lat']), float(row['stop_lon'])))

    # Import linek
    with open(f'{gtfs_dir}/routes.txt', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute('''
                INSERT INTO routes VALUES (?, ?, ?, ?, ?)
            ''', (row['route_id'], row['agency_id'],
                  row['route_short_name'], row['route_long_name'],
                  int(row['route_type'])))

    conn.commit()
    conn.close()
    print(f"Data importována do {db_path}")

# Použití
import_gtfs_to_sqlite('data/mhd', 'transit.db')
```

## Vizualizace

### Export do GeoJSON

```python
import json

def export_stops_geojson(gtfs_dir, output_file):
    """Export zastávek do GeoJSON formátu."""
    features = []

    with open(f'{gtfs_dir}/stops.txt', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for stop in reader:
            lat = float(stop['stop_lat'])
            lon = float(stop['stop_lon'])

            # Přeskočit zastávky bez GPS (0.0, 0.0)
            if lat == 0.0 and lon == 0.0:
                continue

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lon, lat]
                },
                'properties': {
                    'stop_id': stop['stop_id'],
                    'stop_name': stop['stop_name']
                }
            }
            features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"Exportováno {len(features)} zastávek do {output_file}")

# Použití
export_stops_geojson('data/mhd', 'stops.geojson')
```

### Leaflet mapa

```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
</head>
<body>
    <div id="map" style="height: 600px;"></div>

    <script>
        // Vytvoř mapu
        var map = L.map('map').setView([49.8175, 15.473], 7);

        // Přidej tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: 'OpenStreetMap'
        }).addTo(map);

        // Načti a zobraz zastávky
        fetch('stops.geojson')
            .then(response => response.json())
            .then(data => {
                L.geoJSON(data, {
                    onEachFeature: function(feature, layer) {
                        layer.bindPopup(feature.properties.stop_name);
                    }
                }).addTo(map);
            });
    </script>
</body>
</html>
```

## Nástroje třetích stran

### gtfs-kit

```python
import gtfs_kit as gk

# Načti GTFS data
feed = gk.read_feed('data/mhd/', dist_units='km')

# Základní statistiky
print(feed.describe())

# Validace
validation = feed.validate()
print(validation)

# Export do GeoJSON
feed.stops.to_file('stops.geojson', driver='GeoJSON')
```

### OneBusAway

```bash
# Spusť OneBusAway server
java -jar onebusaway-transit-data-federation-builder.jar \
    --gtfs=data/mhd/ \
    --bundle=transit-bundle

# API endpoint
curl http://localhost:8080/api/where/stops-for-location.json?lat=50.0&lon=14.5
```

## Další zdroje

- [GTFS Specification](https://gtfs.org/)
- [GTFS Best Practices](https://gtfs.org/best-practices/)
- [Transitland](https://www.transit.land/)
- [OpenTripPlanner Docs](http://docs.opentripplanner.org/)

---

**Poslední aktualizace:** 2026-02-08
