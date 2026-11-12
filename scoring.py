DEFAULT_METRO_POINTS = 2.0
DEFAULT_TRAIN_POINTS = 3.0
DEFAULT_TRAM_POINTS = 1.0
DEFAULT_BUS_POINTS = 0.1

DEFAULT_POINTS = {
    "metro": DEFAULT_METRO_POINTS,
    "gare": DEFAULT_TRAIN_POINTS,
    "tram": DEFAULT_TRAM_POINTS,
    "bus": DEFAULT_BUS_POINTS,
}


def score_breakdown(correspondences, points=None):
    if points is None:
        points = DEFAULT_POINTS

    breakdown = {
        "points_metro": points["metro"] if correspondences["metro"] else 0.0,
        "points_gare": points["gare"] if correspondences["gare"] else 0.0,
        "points_tram": points["tram"] if correspondences["tram"] else 0.0,
        "points_bus": round(len(correspondences["bus"]) * points["bus"], 1),
    }
    breakdown["score"] = round(sum(breakdown.values()), 1)
    return breakdown


def station_score(station, points=None):
    return score_breakdown(station["correspondance"], points)["score"]
