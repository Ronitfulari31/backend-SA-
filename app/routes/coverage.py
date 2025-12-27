from flask import Blueprint, jsonify
from app.services.fetch.rss_sources import RSS_SOURCES

coverage_bp = Blueprint("coverage", __name__)


@coverage_bp.route("/api/news/coverage", methods=["GET"])
def coverage():
    result = {
        "continents": {},
        "languages": set(),
        "countries": set(),
        "total_sources": len(RSS_SOURCES)
    }

    for src in RSS_SOURCES:
        result["countries"].add(src["country"])
        result["languages"].update(src["language"])

        cont = src["continent"]
        result["continents"].setdefault(cont, [])
        result["continents"][cont].append({
            "name": src["name"],
            "country": src["country"],
            "languages": src["language"],
            "categories": src["category"]
        })

    # Convert sets to lists and sort for determinism
    result["countries"] = sorted(result["countries"])
    result["languages"] = sorted(result["languages"])

    # Sort sources within each continent by name
    for cont in result["continents"]:
        result["continents"][cont].sort(key=lambda x: x["name"])

    # Sort continents dictionary keys alphabetically
    result["continents"] = dict(sorted(result["continents"].items()))

    return jsonify(result)
