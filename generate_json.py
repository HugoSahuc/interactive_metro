import csv
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).parent
TRAIN_STATIONS_PATH = BASE_DIR / "data/gares.geojson"
OUTPUT_PATH = BASE_DIR / "correspondance.json"
NETWORKS = {
    "Tisséo": BASE_DIR / "gtfs/tisseo_gtfs_v2.zip",
    "Ilévia": BASE_DIR / "gtfs/lille_gtfs.zip",
    "RTM": BASE_DIR / "gtfs/mamp-rtm.gtfs.zip",
    "STAR": BASE_DIR / "gtfs/rennes_gtfs.zip",
    "IDFM": BASE_DIR / "gtfs/IDFM-gtfs.zip",
    "TCL": BASE_DIR / "gtfs/TCL.zip",
}

TRAIN_STATION_MAX_DISTANCE_METERS = 300
EARTH_RADIUS_METERS = 6_371_000

TRAM_ROUTE_TYPE = "0"
METRO_ROUTE_TYPE = "1"
BUS_ROUTE_TYPE = "3"


def read_gtfs_file(gtfs_zip, filename):
    with gtfs_zip.open(filename) as file:
        text_file = io.TextIOWrapper(file, encoding="utf-8-sig")
        yield from csv.DictReader(text_file)


def format_route_name(route):
    prefixes = {
        METRO_ROUTE_TYPE: "ligne",
        TRAM_ROUTE_TYPE: "tram",
        BUS_ROUTE_TYPE: "bus",
    }
    prefix = prefixes[route["route_type"]]
    route_name = route["route_short_name"] or route.get("route_long_name", "")
    return f"{prefix} {route_name}".strip()


def route_color(route):
    color = route.get("route_color", "").strip().lstrip("#")
    if len(color) == 6 and all(character in "0123456789abcdefABCDEF" for character in color):
        return f"#{color}"
    return None


def distance_in_meters(first_position, second_position):
    first_lon, first_lat = map(math.radians, first_position)
    second_lon, second_lat = map(math.radians, second_position)
    delta_lon = second_lon - first_lon
    delta_lat = second_lat - first_lat

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(first_lat)
        * math.cos(second_lat)
        * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(haversine))


def find_nearby_train_stations(position, train_stations):
    return sorted(
        train_station["name"]
        for train_station in train_stations
        if distance_in_meters(position, train_station["position"])
        <= TRAIN_STATION_MAX_DISTANCE_METERS
    )


def build_correspondences(
    station_route_ids,
    current_route_id,
    routes_by_id,
    nearby_train_stations,
):
    correspondences = {
        "metro": [],
        "tram": [],
        "bus": [],
        "gare": nearby_train_stations,
    }

    for route_id in station_route_ids:
        if route_id == current_route_id:
            continue

        route = routes_by_id[route_id]
        route_type = route["route_type"]

        if route_type == METRO_ROUTE_TYPE:
            correspondences["metro"].append(format_route_name(route))
        elif route_type == TRAM_ROUTE_TYPE:
            correspondences["tram"].append(format_route_name(route))
        elif route_type == BUS_ROUTE_TYPE:
            correspondences["bus"].append(format_route_name(route))

    correspondences["metro"].sort()
    correspondences["tram"].sort()
    correspondences["bus"].sort()
    return correspondences


def build_network(gtfs_path, train_stations):
    with zipfile.ZipFile(gtfs_path) as gtfs_zip:
        routes = list(read_gtfs_file(gtfs_zip, "routes.txt"))
        routes_by_id = {route["route_id"]: route for route in routes}
        metro_routes = [
            route for route in routes if route["route_type"] == METRO_ROUTE_TYPE
        ]
        metro_route_ids = {route["route_id"] for route in metro_routes}

        trip_route_ids = {}
        first_metro_trip_ids = {}
        direction_zero_trip_ids = {}

        for trip in read_gtfs_file(gtfs_zip, "trips.txt"):
            route_id = trip["route_id"]
            trip_route_ids[trip["trip_id"]] = route_id

            if route_id not in metro_route_ids:
                continue

            first_metro_trip_ids.setdefault(route_id, trip["trip_id"])
            if trip.get("direction_id") == "0":
                direction_zero_trip_ids.setdefault(route_id, trip["trip_id"])

        representative_trip_ids = {
            direction_zero_trip_ids.get(route_id, trip_id): route_id
            for route_id, trip_id in first_metro_trip_ids.items()
        }

        station_names = {}
        station_positions = {}
        parent_station_ids = {}

        for stop in read_gtfs_file(gtfs_zip, "stops.txt"):
            stop_id = stop["stop_id"]
            station_names[stop_id] = stop["stop_name"]
            station_positions[stop_id] = (
                float(stop["stop_lon"]),
                float(stop["stop_lat"]),
            )
            parent_station_ids[stop_id] = stop.get("parent_station") or stop_id

        route_ids_by_station = defaultdict(set)
        metro_station_sequences = defaultdict(list)

        for stop_time in read_gtfs_file(gtfs_zip, "stop_times.txt"):
            trip_id = stop_time["trip_id"]
            route_id = trip_route_ids[trip_id]
            station_id = parent_station_ids[stop_time["stop_id"]]
            route_ids_by_station[station_id].add(route_id)

            if trip_id in representative_trip_ids:
                metro_route_id = representative_trip_ids[trip_id]
                sequence = int(stop_time["stop_sequence"])
                metro_station_sequences[metro_route_id].append((sequence, station_id))

    lines = []
    for route in sorted(metro_routes, key=lambda item: item["route_short_name"]):
        route_id = route["route_id"]
        stations = []

        for _, station_id in sorted(metro_station_sequences[route_id]):
            stations.append(
                {
                    "id": station_id,
                    "name": station_names[station_id],
                    "position": station_positions[station_id],
                    "correspondance": build_correspondences(
                        route_ids_by_station[station_id],
                        route_id,
                        routes_by_id,
                        find_nearby_train_stations(
                            station_positions[station_id],
                            train_stations,
                        ),
                    ),
                }
            )

        line = {
            "id": route_id,
            "type": "metro",
            "name": format_route_name(route),
            "stations": stations,
        }
        color = route_color(route)
        if color:
            line["color"] = color
        lines.append(line)

    return lines


def main():
    with TRAIN_STATIONS_PATH.open(encoding="utf-8") as train_stations_file:
        train_stations_geojson = json.load(train_stations_file)
        train_stations = [
            {
                "name": feature["properties"]["nom"],
                "position": feature["geometry"]["coordinates"],
            }
            for feature in train_stations_geojson["features"]
            if feature["geometry"] and feature["geometry"]["type"] == "Point"
        ]

    output = {}
    for network_name, gtfs_path in NETWORKS.items():
        output[network_name] = build_network(gtfs_path, train_stations)
        print(f"{network_name} : {len(output[network_name])} lignes de métro")

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(output, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")

    print(f"{OUTPUT_PATH.name} généré avec {len(output)} réseaux.")


if __name__ == "__main__":
    main()
