import json
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsPrintLayout,
    QgsProject,
    QgsRectangle,
    QgsUnitTypes,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont

JSON_PATH = Path("/home/hugo/Documents/posts/30MapsDayChallenge2026/interactions/correspondance.json")
LAYOUT_NAME = "post_france"
NETWORK_CITIES = {
    "IDFM": "Paris",
    "Tisséo": "Toulouse",
    "Ilévia": "Lille",
    "RTM": "Marseille",
    "STAR": "Rennes",
    "TCL": "Lyon",
}
PAGE_WIDTH = 2300
PAGE_HEIGHT = 2700
PAGE_MARGIN = 100
COLUMN_GAP = 80
ROW_GAP = 70
TITLE_HEIGHT = 75
TITLE_GAP = 20
EXTENT_MARGIN = 0.12
ALIGNMENT = Qt.AlignmentFlag if hasattr(Qt, "AlignmentFlag") else Qt
try:
    LAYOUT_PIXELS = Qgis.LayoutUnit.Pixels
except AttributeError:
    LAYOUT_PIXELS = QgsUnitTypes.LayoutPixels
SCORE_POINTS = {"metro": 2.0, "gare": 3.0, "tram": 1.0, "bus": 0.1}


def merge_stations(lines):
    stations = {}
    for line in lines:
        for station in line["stations"]:
            station_id = station["id"]
            if station_id not in stations:
                stations[station_id] = {
                    "position": station["position"],
                    "correspondance": {key: set() for key in SCORE_POINTS},
                }
            for kind, values in station["correspondance"].items():
                stations[station_id]["correspondance"][kind].update(values)
    return list(stations.values())


def station_score(correspondences):
    return (
        SCORE_POINTS["metro"] * bool(correspondences["metro"])
        + SCORE_POINTS["gare"] * bool(correspondences["gare"])
        + SCORE_POINTS["tram"] * bool(correspondences["tram"])
        + SCORE_POINTS["bus"] * len(correspondences["bus"])
    )


def network_score(stations):
    return round(sum(station_score(station["correspondance"]) for station in stations), 1)


def formatted_score(score):
    value = f"{score:,.1f}".replace(",", " ").replace(".", ",")
    return value.removesuffix(",0")


def network_extent(stations, transform, aspect_ratio):
    points = [transform.transform(*station["position"]) for station in stations]
    xmin = min(point.x() for point in points)
    xmax = max(point.x() for point in points)
    ymin = min(point.y() for point in points)
    ymax = max(point.y() for point in points)
    center_x = (xmin + xmax) / 2
    center_y = (ymin + ymax) / 2
    width = max(xmax - xmin, 1e-9)
    height = max(ymax - ymin, 1e-9)

    if width / height < aspect_ratio:
        width = height * aspect_ratio
    else:
        height = width / aspect_ratio

    width *= 1 + 2 * EXTENT_MARGIN
    height *= 1 + 2 * EXTENT_MARGIN
    return QgsRectangle(
        center_x - width / 2,
        center_y - height / 2,
        center_x + width / 2,
        center_y + height / 2,
    )


def add_title(layout, text, x, y, width):
    label = QgsLayoutItemLabel(layout)
    label.setText(text)
    font = QFont("Montserrat", 11)
    font.setBold(True)
    label.setFont(font)
    label.setFontColor(QColor("#171717"))
    label.setHAlign(ALIGNMENT.AlignHCenter)
    label.setVAlign(ALIGNMENT.AlignVCenter)
    label.attemptMove(QgsLayoutPoint(x, y, LAYOUT_PIXELS))
    label.attemptResize(QgsLayoutSize(width, TITLE_HEIGHT, LAYOUT_PIXELS))
    layout.addLayoutItem(label)


def add_map(layout, layers, extent, x, y, width, height):
    map_item = QgsLayoutItemMap(layout)
    map_item.setLayers(layers)
    map_item.setKeepLayerSet(True)
    map_item.setBackgroundColor(QColor("#f7f5f0"))
    map_item.attemptMove(QgsLayoutPoint(x, y, LAYOUT_PIXELS))
    map_item.attemptResize(QgsLayoutSize(width, height, LAYOUT_PIXELS))
    map_item.setExtent(extent)
    layout.addLayoutItem(map_item)


def create_layout():
    with JSON_PATH.open(encoding="utf-8") as file:
        networks = json.load(file)

    missing_networks = [name for name in NETWORK_CITIES if name not in networks]
    if missing_networks:
        raise ValueError(f"Réseaux absents du JSON : {', '.join(missing_networks)}")

    project = QgsProject.instance()
    layers = [layer for layer in project.layerTreeRoot().checkedLayers() if layer.isSpatial()]
    if not layers:
        raise RuntimeError("Aucune couche spatiale visible dans le projet QGIS.")

    project_crs = project.crs()
    if not project_crs.isValid():
        raise RuntimeError("Le SCR du projet QGIS n'est pas défini.")

    source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    transform = QgsCoordinateTransform(source_crs, project_crs, project)
    manager = project.layoutManager()
    existing_layout = manager.layoutByName(LAYOUT_NAME)
    if existing_layout:
        manager.removeLayout(existing_layout)

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(LAYOUT_NAME)
    layout.renderContext().setDpi(300)
    page = layout.pageCollection().page(0)
    page.setPageSize(
        QgsLayoutSize(PAGE_WIDTH, PAGE_HEIGHT, LAYOUT_PIXELS)
    )

    cell_width = (PAGE_WIDTH - 2 * PAGE_MARGIN - COLUMN_GAP) / 2
    cell_height = (PAGE_HEIGHT - 2 * PAGE_MARGIN - 2 * ROW_GAP) / 3
    map_height = cell_height - TITLE_HEIGHT - TITLE_GAP
    aspect_ratio = cell_width / map_height

    network_maps = []
    for network_name, city in NETWORK_CITIES.items():
        stations = merge_stations(networks[network_name])
        network_maps.append((network_score(stations), city, network_name, stations))
    network_maps.sort(reverse=True, key=lambda item: item[0])

    for index, (score, city, network_name, stations) in enumerate(network_maps):
        column = index % 2
        row = index // 2
        x = PAGE_MARGIN + column * (cell_width + COLUMN_GAP)
        y = PAGE_MARGIN + row * (cell_height + ROW_GAP)
        extent = network_extent(stations, transform, aspect_ratio)
        title = f"{city} - {network_name} - {formatted_score(score)} points"
        add_title(layout, title, x, y, cell_width)
        add_map(
            layout,
            layers,
            extent,
            x,
            y + TITLE_HEIGHT + TITLE_GAP,
            cell_width,
            map_height,
        )

    manager.addLayout(layout)
    print(f"Mise en page '{LAYOUT_NAME}' créée avec succès.")


create_layout()
