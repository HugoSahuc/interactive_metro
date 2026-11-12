import argparse
import json
from pathlib import Path

from scoring import DEFAULT_POINTS, score_breakdown


BASE_DIR = Path(__file__).parent
DEFAULT_INPUT_PATH = BASE_DIR / "correspondance.json"
DEFAULT_OUTPUT_PATH = BASE_DIR / "metro_qgis.geojson"
VALUE_SEPARATOR = " | "


def joined(values):
    return VALUE_SEPARATOR.join(sorted(set(values)))



def station_properties(network_name, station):
    correspondences = station["correspondance"]
    properties = {
        "feature_type": "station",
        "network": network_name,
        "station_id": station["id"],
        "station": station["name"],
        "metro_lines": joined(correspondences["metro"]),
        "tram_lines": joined(correspondences["tram"]),
        "bus_lines": joined(correspondences["bus"]),
        "train_stations": joined(correspondences["gare"]),
        "metro_count": len(correspondences["metro"]),
        "tram_count": len(correspondences["tram"]),
        "bus_count": len(correspondences["bus"]),
        "train_station_count": len(correspondences["gare"]),
        "has_metro_connection": bool(correspondences["metro"]),
        "has_tram": bool(correspondences["tram"]),
        "has_bus": bool(correspondences["bus"]),
        "has_train_station": bool(correspondences["gare"]),
        "weight_metro": DEFAULT_POINTS["metro"],
        "weight_gare": DEFAULT_POINTS["gare"],
        "weight_tram": DEFAULT_POINTS["tram"],
        "weight_bus": DEFAULT_POINTS["bus"],
    }
    properties.update(score_breakdown(correspondences))
    return properties


def merge_station(existing_station, line_name, station):
    existing_station["lines"].add(line_name)
    for connection_type, values in station["correspondance"].items():
        existing_station["correspondance"][connection_type].update(values)


def build_features(networks):
    features = []
    stations = {}

    for network_name, lines in networks.items():
        for line in lines:
            coordinates = [station["position"] for station in line["stations"]]
            coordinates = [
                position
                for index, position in enumerate(coordinates)
                if index == 0 or position != coordinates[index - 1]
            ]

            if len(coordinates) < 2:
                print(
                    f"Attention : {network_name} — {line['name']} ignorée "
                    "car elle contient moins de deux coordonnées distinctes."
                )
                continue

            line_scores = [
                score_breakdown(station["correspondance"])["score"]
                for station in line["stations"]
            ]
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "feature_type": "metro_line",
                        "network": network_name,
                        "line_id": line["id"],
                        "line": line["name"],
                        "color": line.get("color", ""),
                        "station_count": len(line["stations"]),
                        "score": round(sum(line_scores), 1),
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                }
            )

            for station in line["stations"]:
                key = (network_name, station["id"])
                if key not in stations:
                    stations[key] = {
                        "id": station["id"],
                        "name": station["name"],
                        "position": station["position"],
                        "lines": set(),
                        "correspondance": {
                            "metro": set(),
                            "tram": set(),
                            "bus": set(),
                            "gare": set(),
                        },
                    }
                merge_station(stations[key], line["name"], station)

    for (network_name, _), station in sorted(
        stations.items(),
        key=lambda item: (item[0][0].casefold(), item[1]["name"].casefold()),
    ):
        correspondences = {
            connection_type: sorted(values)
            for connection_type, values in station["correspondance"].items()
        }
        point_station = {
            "id": station["id"],
            "name": station["name"],
            "correspondance": correspondences,
        }
        properties = station_properties(network_name, point_station)
        properties["served_metro_lines"] = joined(station["lines"])
        properties["served_metro_count"] = len(station["lines"])

        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": "Point",
                    "coordinates": station["position"],
                },
            }
        )

    return features


def parse_args():
    parser = argparse.ArgumentParser(
        description="Transforme correspondance.json en GeoJSON pour QGIS."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Fichier source (défaut : {DEFAULT_INPUT_PATH.name}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Fichier GeoJSON de sortie (défaut : {DEFAULT_OUTPUT_PATH.name}).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    with args.input.open(encoding="utf-8") as input_file:
        networks = json.load(input_file)

    features = build_features(networks)
    geojson = {
        "type": "FeatureCollection",
        "name": "metro_qgis",
        "properties": {
            "score_points_metro": DEFAULT_POINTS["metro"],
            "score_points_gare": DEFAULT_POINTS["gare"],
            "score_points_tram": DEFAULT_POINTS["tram"],
            "score_points_bus": DEFAULT_POINTS["bus"],
        },
        "features": features,
    }
    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(geojson, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")

    line_count = sum(
        feature["properties"]["feature_type"] == "metro_line"
        for feature in features
    )
    print(
        f"{args.output} généré avec {line_count} lignes "
        f"et {len(features) - line_count} stations."
    )


if __name__ == "__main__":
    main()
