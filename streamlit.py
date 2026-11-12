import json
import re
from html import escape
from pathlib import Path

import streamlit as st

from scoring import (
    DEFAULT_BUS_POINTS,
    DEFAULT_METRO_POINTS,
    DEFAULT_TRAIN_POINTS,
    DEFAULT_TRAM_POINTS,
    station_score,
)


DATA_FILE = Path(__file__).with_name("correspondance.json")
FALLBACK_LINE_COLORS = ["#e11d48", "#2563eb", "#7c3aed", "#0891b2"]


st.set_page_config(
    page_title="Score des correspondances — Réseaux de métro",
    page_icon="🚇",
    layout="wide",
)


@st.cache_data
def load_networks(path: Path) -> dict[str, list[dict]]:
    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    if "toulouse" in data:
        return {"Tisséo": data["toulouse"]}
    return data



def line_connection_counts(line: dict) -> dict[str, int]:
    stations = line["stations"]
    train_stations = {
        train
        for station in stations
        for train in station["correspondance"]["gare"]
    }

    return {
        "metro": sum(len(station["correspondance"]["metro"]) for station in stations),
        "tram": sum(len(station["correspondance"]["tram"]) for station in stations),
        "bus": sum(len(station["correspondance"]["bus"]) for station in stations),
        "gare": len(train_stations),
    }


def format_score(score: float) -> str:
    return f"{score:.1f}".replace(".", ",")


def natural_line_sort_key(line: dict) -> tuple:
    parts = re.split(r"(\d+)", line["name"].casefold())
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in parts
        if part
    )


def connection_badge(icon: str, label: str, values: list[str], kind: str) -> str:
    if not values:
        return ""

    details = escape(", ".join(values), quote=True)
    count = (
        f'<span class="connection-count">{len(values)}</span>'
        if kind == "metro" and len(values) > 1
        else ""
    )
    return (
        f'<span class="connection-badge {kind}" title="{details}">'
        f'<span aria-hidden="true">{icon}</span>{count}'
        f'<span class="sr-only">{label} : {details}</span>'
        "</span>"
    )


def render_metro_map(line: dict, points: dict[str, float], color: str) -> str:
    station_items = []

    for station in line["stations"]:
        connections = station["correspondance"]
        bus_count = len(connections["bus"])
        bus_details = escape(", ".join(connections["bus"]), quote=True)
        bus_class = "bus" if bus_count else "bus empty"
        badges = "".join(
            [
                connection_badge("M", "Métro", connections["metro"], "metro"),
                connection_badge("T", "Tram", connections["tram"], "tram"),
                connection_badge("◆", "Gare", connections["gare"], "train"),
                (
                    f'<span class="connection-badge {bus_class}" '
                    f'title="{bus_details or "Aucune ligne de bus"}">'
                    f'🚌 {bus_count}</span>'
                ),
            ]
        )
        station_items.append(
            '<div class="station-item">'
            '<div class="station-node"></div>'
            f'<div class="station-name">{escape(station["name"])}</div>'
            f'<div class="station-connections">{badges}</div>'
            f'<div class="station-points">'
            f'{format_score(station_score(station, points))} pts'
            "</div>"
            "</div>"
        )

    return (
        f'<div class="metro-map" style="--line-color: {color}">'
        f'<div class="metro-track">{"".join(station_items)}</div>'
        "</div>"
    )


st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(circle at 10% 5%, rgba(236, 72, 153, 0.08), transparent 25rem),
                radial-gradient(circle at 90% 15%, rgba(14, 165, 233, 0.09), transparent 28rem);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 0.8rem;
            padding: 0.7rem 1rem;
        }
        [data-testid="stMetricValue"] {
            color: #e11d48;
        }
        .line-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin: 1.5rem 0 0.65rem;
        }
        .line-dot {
            width: 1rem;
            height: 1rem;
            border-radius: 50%;
            background: var(--line-color);
            box-shadow: 0 0 0 0.25rem color-mix(in srgb, var(--line-color) 18%, transparent);
        }
        .line-header h3 {
            margin: 0;
        }
        .line-stats {
            display: grid;
            grid-template-columns: repeat(6, minmax(7rem, 1fr));
            gap: 0.45rem;
            margin-bottom: 0.7rem;
        }
        .line-stat {
            padding: 0.55rem 0.7rem;
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 0.65rem;
            background: rgba(255, 255, 255, 0.035);
        }
        .line-stat-value {
            display: block;
            font-size: 1.15rem;
            font-weight: 750;
            color: var(--line-color);
            line-height: 1.2;
        }
        .line-stat-label {
            font-size: 0.72rem;
            opacity: 0.72;
        }
        .metro-map {
            overflow-x: auto;
            padding: 0.2rem 0 0.7rem;
            scrollbar-width: thin;
        }
        .metro-track {
            display: flex;
            width: max-content;
            min-width: 100%;
            padding: 0.5rem 0.9rem 0.2rem;
        }
        .station-item {
            position: relative;
            width: 8rem;
            flex: 0 0 8rem;
            padding-top: 1.25rem;
            text-align: center;
        }
        .station-item::before {
            content: "";
            position: absolute;
            top: 0.38rem;
            left: 0;
            width: 100%;
            height: 0.3rem;
            background: var(--line-color);
        }
        .station-item:first-child::before {
            left: 50%;
            width: 50%;
        }
        .station-item:last-child::before {
            width: 50%;
        }
        .station-node {
            position: absolute;
            z-index: 1;
            top: 0;
            left: calc(50% - 0.45rem);
            width: 0.9rem;
            height: 0.9rem;
            border: 0.22rem solid var(--line-color);
            border-radius: 50%;
            background: var(--background-color);
        }
        .station-name {
            display: flex;
            align-items: flex-start;
            justify-content: center;
            height: 2.8rem;
            padding: 0 0.3rem;
            font-size: 0.78rem;
            font-weight: 650;
            line-height: 1.15;
        }
        .station-connections {
            display: flex;
            min-height: 1.55rem;
            align-items: center;
            justify-content: center;
            gap: 0.2rem;
        }
        .connection-badge {
            display: inline-flex;
            min-width: 1.25rem;
            height: 1.25rem;
            padding: 0 0.28rem;
            align-items: center;
            justify-content: center;
            border-radius: 0.35rem;
            font-size: 0.68rem;
            font-weight: 800;
            color: white;
            cursor: help;
        }
        .connection-badge.metro { background: #2563eb; }
        .connection-count {
            margin-left: 0.15rem;
            font-size: 0.55rem;
            line-height: 1;
        }
        .connection-badge.tram { background: #7c3aed; }
        .connection-badge.train { background: #0891b2; }
        .connection-badge.bus { background: #475569; }
        .connection-badge.empty { opacity: 0.35; }
        .station-points {
            margin-top: 0.2rem;
            font-size: 0.68rem;
            font-weight: 700;
            color: var(--line-color);
        }
        .station-ranking {
            display: grid;
            grid-template-columns: repeat(5, minmax(8rem, 1fr));
            gap: 0.65rem;
            margin-bottom: 1.2rem;
        }
        .station-rank {
            padding: 0.8rem 0.9rem;
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 0.8rem;
            background: rgba(255, 255, 255, 0.035);
        }
        .station-rank-position {
            font-size: 0.75rem;
            font-weight: 750;
            opacity: 0.65;
        }
        .station-rank-name {
            min-height: 2.8rem;
            margin: 0.2rem 0;
            font-weight: 700;
            line-height: 1.2;
        }
        .station-rank-score {
            color: #e11d48;
            font-size: 1.2rem;
            font-weight: 750;
        }
        .station-rank-network {
            font-size: 0.75rem;
            opacity: 0.7;
        }
        .map-legend {
            font-size: 0.75rem;
            opacity: 0.75;
            margin-bottom: -0.6rem;
        }
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
        @media (max-width: 900px) {
            .line-stats {
                grid-template-columns: repeat(3, 1fr);
            }
            .station-ranking {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚇 Score des correspondances")

st.sidebar.header("⚙️ Système de points")
st.sidebar.caption("Modifiez les valeurs pour recalculer tous les scores.")
points = {
    "metro": st.sidebar.number_input(
        "Correspondance métro",
        min_value=0.0,
        value=DEFAULT_METRO_POINTS,
        step=1.0,
        format="%.0f",
    ),
    "gare": st.sidebar.number_input(
        "Correspondance gare",
        min_value=0.0,
        value=DEFAULT_TRAIN_POINTS,
        step=1.0,
        format="%.0f",
    ),
    "tram": st.sidebar.number_input(
        "Correspondance tram",
        min_value=0.0,
        value=DEFAULT_TRAM_POINTS,
        step=1.0,
        format="%.0f",
    ),
    "bus": st.sidebar.number_input(
        "Par ligne de bus",
        min_value=0.0,
        value=DEFAULT_BUS_POINTS,
        step=0.1,
        format="%.1f",
    ),
}


try:
    networks = load_networks(DATA_FILE)
except (FileNotFoundError, json.JSONDecodeError, KeyError) as error:
    st.error(f"Impossible de charger les données : {error}")
    st.stop()

network_scores = {
    network_name: round(
        sum(
            station_score(station, points)
            for line in lines
            for station in line["stations"]
        ),
        1,
    )
    for network_name, lines in networks.items()
}
ordered_networks = sorted(
    networks.items(),
    key=lambda item: (-network_scores[item[0]], item[0].casefold()),
)
total_score = round(sum(network_scores.values()), 1)
total_lines = sum(len(lines) for lines in networks.values())
total_stations = sum(
    len(line["stations"]) for lines in networks.values() for line in lines
)
connected_stations = sum(
    any(station["correspondance"][kind] for kind in ("metro", "tram", "bus", "gare"))
    for lines in networks.values()
    for line in lines
    for station in line["stations"]
)

metric_columns = st.columns(4)
metric_columns[0].metric("Score total", f"{format_score(total_score)} pts")
metric_columns[1].metric("Réseaux", len(networks))
metric_columns[2].metric("Lignes", total_lines)
metric_columns[3].metric("Stations connectées", f"{connected_stations} / {total_stations}")

st.subheader("Scores par réseau")
network_columns = st.columns(len(network_scores))
for column, (network_name, _) in zip(network_columns, ordered_networks):
    column.metric(network_name, f"{format_score(network_scores[network_name])} pts")

stations_by_network_and_name = {}
for network_name, lines in ordered_networks:
    for line in lines:
        for station in line["stations"]:
            key = (network_name, station["name"])
            score = station_score(station, points)
            stations_by_network_and_name[key] = max(
                score,
                stations_by_network_and_name.get(key, 0.0),
            )

top_stations = sorted(
    (
        (station_name, network_name, score)
        for (network_name, station_name), score in stations_by_network_and_name.items()
    ),
    key=lambda item: (-item[2], item[0].casefold(), item[1].casefold()),
)[:5]

st.subheader("Scores par station · Top 5")
station_ranking_html = "".join(
    '<div class="station-rank">'
    f'<div class="station-rank-position">N° {rank}</div>'
    f'<div class="station-rank-name">{escape(station_name)}</div>'
    f'<div class="station-rank-score">{format_score(score)} pts</div>'
    f'<div class="station-rank-network">{escape(network_name)}</div>'
    "</div>"
    for rank, (station_name, network_name, score) in enumerate(top_stations, start=1)
)
st.markdown(
    f'<div class="station-ranking">{station_ranking_html}</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="map-legend">'
    '<strong>Légende :</strong> M métro · T tram · ◆ gare · 🚌 nombre de lignes de bus'
    "</div>",
    unsafe_allow_html=True,
)

for network_name, lines in ordered_networks:
    st.markdown(
        f"## {escape(network_name)} · {format_score(network_scores[network_name])} pts"
    )

    for line_index, line in enumerate(sorted(lines, key=natural_line_sort_key)):
        score = round(
            sum(station_score(station, points) for station in line["stations"]), 1
        )
        counts = line_connection_counts(line)
        color = line.get("color") or FALLBACK_LINE_COLORS[
            line_index % len(FALLBACK_LINE_COLORS)
        ]
        stats = [
            (f"{format_score(score)} pts", "Score"),
            (str(len(line["stations"])), "Stations"),
            (str(counts["metro"]), "Correspondances métro"),
            (str(counts["tram"]), "Correspondances tram"),
            (str(counts["bus"]), "Correspondances bus"),
            (str(counts["gare"]), "Gares desservies"),
        ]
        stats_html = "".join(
            f'<div class="line-stat"><span class="line-stat-value">{value}</span>'
            f'<span class="line-stat-label">{label}</span></div>'
            for value, label in stats
        )

        line_html = (
            f'<section style="--line-color: {color}">'
            '<div class="line-header">'
            '<span class="line-dot"></span>'
            f'<h3>{escape(line["name"].title())}</h3>'
            "</div>"
            f'<div class="line-stats">{stats_html}</div>'
            f'{render_metro_map(line, points, color)}'
            "</section>"
        )
        st.markdown(line_html, unsafe_allow_html=True)

st.caption(f"Source : {DATA_FILE.name} · Total général : {format_score(total_score)} points")
