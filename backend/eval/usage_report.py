"""Turn the anonymous usage log into a report after a round of manual testing.

    cd backend
    python -m eval.usage_report                     # reads metrics/sessions.jsonl
    python -m eval.usage_report --file other.jsonl
    python -m eval.usage_report --reset             # start a fresh log before a new test round

Writes eval/results/USAGE.md.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from app import metrics  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path)
    ap.add_argument("--reset", action="store_true", help="archive the current log and start a new one")
    args = ap.parse_args()
    path = args.file or metrics.metrics_file()

    if args.reset:
        if path.exists():
            archived = path.with_name(f"sessions_{datetime.now():%Y%m%d_%H%M}.jsonl")
            path.rename(archived)
            print(f"Old log saved as {archived.name}. New sessions will start a fresh log.")
        else:
            print("No log yet - nothing to reset.")
        return

    records = metrics.load_records(path)
    if not records:
        sys.exit(f"No sessions recorded yet in {path}. Fill some forms in the app first.")
    s = metrics.summarize(records)
    via = s["answers_by_input_pct"]
    lines = [
        "# Form Saathi usage report", "",
        f"From {len(records)} sessions recorded in `{path.name}` (counts only - no answers are stored).", "",
        "| Measure | Value |", "|---|---|",
        f"| Sessions | {s['sessions']} |",
        f"| Completed | {s['completed']} ({s['completion_rate_pct']}%) |",
        f"| Median time to complete a form | {s['median_minutes_to_complete']} min |",
        f"| Median chat turns to complete | {s['median_turns_to_complete']} |",
        f"| Invalid inputs caught before the form was finished | {s['invalid_inputs_caught']} |",
        f"| \"What does this mean?\" requests | {s['explain_requests']} |",
        f"| Corrections made | {s['corrections']} |",
        f"| Answers typed / tapped / spoken | {via.get('text', 0)}% / {via.get('tap', 0)}% / {via.get('voice', 0)}% |",
        f"| Median response time | {s['median_response_ms']} ms |",
        "", "## Invalid inputs caught, by type", "", "| Type | Count |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in s["invalid_inputs_by_type"].items()],
        "", "## Sessions by language", "", "| Language | Sessions |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in s["by_language"].items()],
        "", "## Sessions by form", "", "| Form | Sessions |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in s["by_form"].items()], "",
    ]
    out = HERE / "results" / "USAGE.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
