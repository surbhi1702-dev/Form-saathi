"""Anonymous usage metrics.

For each session we keep only COUNTS - never what the person typed or any field value:
form, language, time taken, number of turns, invalid inputs caught (by error type),
"what does this mean?" requests, corrections, skips, how answers were given
(typed / tapped / spoken) and response times.

A record is appended to METRICS_FILE (JSON lines) when a session is completed,
deleted or expires. `summarize()` turns those records into the numbers for a report.
"""
from __future__ import annotations

import json
import os
import statistics
import threading
import time
from collections import Counter
from pathlib import Path

_lock = threading.Lock()
DEFAULT_FILE = Path(__file__).resolve().parent.parent / "metrics" / "sessions.jsonl"


def metrics_file() -> Path:
    return Path(os.getenv("METRICS_FILE", str(DEFAULT_FILE)))


def new_session(form_id: str | None, lang: str) -> dict:
    return {"form_id": form_id, "lang": lang, "started": time.time(), "turns": 0, "invalid_inputs": 0,
            "error_types": Counter(), "explains": 0, "corrections": 0, "skips": 0,
            "via": Counter(), "turn_ms": [], "language_changes": 0, "written": False}


def record_turn(m: dict, *, intent: str | None, error: str | None, via: str, ms: float) -> None:
    m["turns"] += 1
    m["via"][via] += 1
    m["turn_ms"].append(round(ms, 1))
    if error and error != "cannot_skip":
        m["invalid_inputs"] += 1
        m["error_types"][error] += 1
    if intent == "explain":
        m["explains"] += 1
    elif intent == "correct":
        m["corrections"] += 1
    elif intent == "skip" and error != "cannot_skip":
        m["skips"] += 1


def finish(m: dict, *, completed: bool, fields_answered: int, fields_total: int) -> None:
    """Write the session's record once. Safe to call more than once."""
    if m.get("written") or m["turns"] == 0:
        return
    m["written"] = True
    ms = sorted(m["turn_ms"])
    record = {
        "ts": round(time.time()), "form_id": m["form_id"], "lang": m["lang"], "completed": completed,
        "duration_s": round(time.time() - m["started"], 1), "turns": m["turns"],
        "fields_answered": fields_answered, "fields_total": fields_total,
        "invalid_inputs": m["invalid_inputs"], "error_types": dict(m["error_types"]),
        "explains": m["explains"], "corrections": m["corrections"], "skips": m["skips"],
        "via": dict(m["via"]), "language_changes": m["language_changes"],
        "median_turn_ms": round(statistics.median(ms)) if ms else None,
        "max_turn_ms": round(ms[-1]) if ms else None,
    }
    path = metrics_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _lock, open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # metrics are best-effort; never break the app


def load_records(path: Path | None = None) -> list[dict]:
    path = path or metrics_file()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _median(values):
    return round(statistics.median(values), 1) if values else None


def summarize(records: list[dict]) -> dict:
    done = [r for r in records if r.get("completed")]
    via = Counter()
    errors = Counter()
    for r in records:
        via.update(r.get("via", {}))
        errors.update(r.get("error_types", {}))
    answers = sum(via.values())
    return {
        "sessions": len(records),
        "completed": len(done),
        "completion_rate_pct": round(100 * len(done) / len(records), 1) if records else None,
        "median_minutes_to_complete": _median([r["duration_s"] / 60 for r in done]),
        "median_turns_to_complete": _median([r["turns"] for r in done]),
        "invalid_inputs_caught": sum(r.get("invalid_inputs", 0) for r in records),
        "invalid_inputs_by_type": dict(errors.most_common()),
        "explain_requests": sum(r.get("explains", 0) for r in records),
        "corrections": sum(r.get("corrections", 0) for r in records),
        "answers_by_input_pct": {k: round(100 * v / answers, 1) for k, v in via.items()} if answers else {},
        "median_response_ms": _median([r["median_turn_ms"] for r in records if r.get("median_turn_ms") is not None]),
        "by_language": dict(Counter(r.get("lang") for r in records)),
        "by_form": dict(Counter(r.get("form_id") for r in records)),
    }
