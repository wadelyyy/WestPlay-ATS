#!/usr/bin/env python3
"""Summarize recorded bridge observations without claiming visual/gameplay success."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path


def stats(values):
    numbers = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    if not numbers:
        return None
    return {"min": min(numbers), "median": statistics.median(numbers), "max": max(numbers)}


def summarize(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    live = [r for r in rows if r.get("mapping") == "available" and not r.get("telemetry", {}).get("paused", True)]
    moving = [r for r in live if abs(r["telemetry"].get("speed_km_h", 0)) > 1]
    positions = [r["telemetry"]["position_m"] for r in live]
    displacement = math.dist(positions[0], positions[-1]) if len(positions) > 1 else None
    result = {
        "file": path.name, "samples": len(rows), "unpaused_samples": len(live),
        "moving_samples_over_1_km_h": len(moving),
        "first_utc": rows[0]["utc"] if rows else None, "last_utc": rows[-1]["utc"] if rows else None,
        "net_displacement_m": displacement,
        "speed_km_h": stats(r["telemetry"].get("speed_km_h") for r in live),
        "heading_turns": stats(r["telemetry"].get("heading_turns") for r in live),
        "navigation_distance_m": stats(r["telemetry"].get("navigation_distance_m") for r in live),
        "present_calls_per_s": stats(r.get("plugin", {}).get("present_rate_fps") for r in live),
        "published_frames_per_s": stats(r.get("host", {}).get("published_rate_fps") for r in live),
        "screen_age_present_calls": stats(r.get("plugin", {}).get("screen_age_frames") for r in live),
        "vehicles": sorted({r.get("vehicle", {}).get("id", "") for r in live}),
        "screen_layouts": sorted({r.get("plugin", {}).get("screen_layout", "") for r in live}),
        "route_answers": sorted({r.get("route_command", {}).get("answer_name", "") for r in live}),
    }
    for process in ("game", "host"):
        samples = [r.get("processes", {}).get(process, {}) for r in live]
        result[process] = {key: stats(p.get(key) for p in samples) for key in
                           ("cpu_pct_system", "cpu_pct_one_core", "working_set_mb")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "measurement_notes": [
            "Only unpaused bridge samples enter statistics; menu/loading samples may still be present.",
            "Present calls are plugin hook observations, not displayed/Frame Generation FPS or a frame-time benchmark.",
            "Published UI frames may be low on static pages; that is not the game frame rate.",
            "Host CPU/RSS covers westplay.exe only, excluding WebView2 child processes. No before/after overhead is inferred.",
            "Position/route statistics do not replace visual checks or prove arrival at a destination.",
        ],
        "recordings": [summarize(path) for path in args.files],
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(args.output)


if __name__ == "__main__":
    main()
