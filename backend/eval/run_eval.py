"""Measure Form Saathi on labelled test sets.

    cd backend
    python -m eval.run_eval              # rules-only, plus Groq if GROQ_API_KEY is set
    python -m eval.run_eval --mode rules # no API key needed
    python -m eval.run_eval --mode llm   # Groq only

What it measures
  intent      - is a message an answer, a question, a skip or a correction?   (eval/data/intent.jsonl)
  extraction  - is the right value pulled out of a messy reply, and are invalid
                values rejected?                                                (eval/data/extraction.jsonl)
  rag         - does the retriever return the right rule note?               (eval/data/rag.jsonl)
  turns       - response time per chat turn and LLM calls per turn, from scripted conversations

Each test set is a plain JSONL file: open it, check the labels, and add your own rows.
Results are written to eval/results/ (EVAL.md, eval_results.json, failures_<mode>.jsonl).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault("LLM_MAX_RPM", "25")  # stay under Groq free-tier per-minute limits

from app import llm as llm_module  # noqa: E402
from app.agents import nodes  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.forms import engine  # noqa: E402
from app.rag.retriever import retrieve  # noqa: E402
from app.validators import gstin_checksum  # noqa: E402

DATA = HERE / "data"
RESULTS = HERE / "results"


def load(name: str) -> list[dict]:
    return [json.loads(l) for l in (DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def set_mode(mode: str) -> None:
    os.environ["FORMSAATHI_MOCK_LLM"] = "1" if mode == "rules" else "0"
    llm_module.set_llm(None)
    llm_module.reset_stats()


def pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def base_state(row: dict) -> dict:
    # Fields that only appear after another answer (show_if) need that answer filled in first.
    values, form = {}, engine.get_form(row["form_id"])
    cond = (engine.field_by_id(form, row["field_id"]) or {}).get("show_if")
    if cond:
        values[cond["field"]] = cond.get("equals") or (cond.get("in") or [None])[0] or "x"
    return {"form_id": row["form_id"], "current_field": row["field_id"], "stage": "filling", "lang": row["lang"],
            "user_message": row["text"], "values": values, "skipped": [], "tcache": {}, "notes": {},
            "reply_parts": []}


# ------------------------------------------------------------------ intent
def eval_intent(rows: list[dict]) -> tuple[dict, list[dict]]:
    by_lang, by_class, confusion, failures = defaultdict(list), defaultdict(list), Counter(), []
    for row in rows:
        got = nodes.classify(base_state(row)).get("intent")
        ok = got == row["expected"]
        by_lang[row["lang"]].append(ok)
        by_class[row["expected"]].append(ok)
        confusion[(row["expected"], got)] += 1
        if not ok:
            failures.append({"set": "intent", **row, "got": got})
    allok = [ok for v in by_lang.values() for ok in v]
    return {
        "n": len(rows), "accuracy": pct(sum(allok), len(allok)),
        "by_language": {k: {"n": len(v), "accuracy": pct(sum(v), len(v))} for k, v in sorted(by_lang.items())},
        "by_class": {k: {"n": len(v), "recall": pct(sum(v), len(v))} for k, v in sorted(by_class.items())},
        "confusion": {f"{e}->{g}": c for (e, g), c in sorted(confusion.items()) if e != g},
    }, failures


# ------------------------------------------------------------------ extraction
def _expected(value):
    first14 = "33ABCDE1234F1Z"
    good = first14 + gstin_checksum(first14)
    bad = first14 + ("0" if good[-1] != "0" else "1")
    return {"__today__": date.today().strftime("%d/%m/%Y"), "__gstin__": good, "__gstin_lower__": good.lower(),
            "__gstin_bad__": bad}.get(value, value) if isinstance(value, str) else value


def _match(got, expected) -> bool:
    if isinstance(expected, list):
        return str(got).strip().lower() in {e.lower() for e in expected}
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return abs(float(got) - float(expected)) < 0.006
        except (TypeError, ValueError):
            return False
    return str(got) == str(expected)


def eval_extraction(rows: list[dict]) -> tuple[dict, list[dict]]:
    outcomes, by_lang, failures = Counter(), defaultdict(list), []
    for row in rows:
        row = {**row, "text": _expected(row["text"]), "expected": _expected(row["expected"])}
        res = nodes.extract_validate(base_state(row))
        got = None if res.get("error") else res.get("values", {}).get(row["field_id"])
        exp = row["expected"]
        if exp is None:
            outcome = "correctly_rejected" if got is None else "wrongly_accepted"
        elif got is None:
            outcome = "wrongly_rejected"
        else:
            outcome = "correct" if _match(got, exp) else "wrong_value"
        ok = outcome in {"correct", "correctly_rejected"}
        outcomes[outcome] += 1
        by_lang[row["lang"]].append(ok)
        if not ok:
            failures.append({"set": "extraction", **row, "got": got, "outcome": outcome, "error": res.get("error")})
    total = len(rows)
    should_accept = outcomes["correct"] + outcomes["wrong_value"] + outcomes["wrongly_rejected"]
    should_reject = outcomes["correctly_rejected"] + outcomes["wrongly_accepted"]
    return {
        "n": total, "accuracy": pct(outcomes["correct"] + outcomes["correctly_rejected"], total),
        "valid_inputs_extracted_correctly": pct(outcomes["correct"], should_accept),
        "invalid_inputs_rejected": pct(outcomes["correctly_rejected"], should_reject),
        "outcomes": dict(outcomes),
        "by_language": {k: {"n": len(v), "accuracy": pct(sum(v), len(v))} for k, v in sorted(by_lang.items())},
    }, failures


# ------------------------------------------------------------------ RAG
def eval_rag(rows: list[dict]) -> tuple[dict, list[dict]]:
    headings = {(c.tag, c.heading) for c in __import__("app.rag.retriever", fromlist=["get_index"]).get_index().chunks}
    for r in rows:
        if (r["expected_tag"], r["expected_heading"]) not in headings:
            raise ValueError(f"RAG label points to a heading that doesn't exist: {r}")
    out, failures = {}, []
    for setting in ("filtered_by_form", "all_notes"):
        hit1 = hit3 = 0
        rr = []
        for r in rows:
            tags = engine.get_form(r["form_id"]).get("knowledge_tags") if setting == "filtered_by_form" else None
            got = [(c.tag, c.heading) for c in retrieve(r["question"], tags=tags, k=3)]
            target = (r["expected_tag"], r["expected_heading"])
            rank = got.index(target) + 1 if target in got else None
            hit1 += rank == 1
            hit3 += rank is not None
            rr.append(1 / rank if rank else 0)
            if rank is None and setting == "all_notes":
                failures.append({"set": "rag", **r, "got": got})
        out[setting] = {"n": len(rows), "hit_at_1": pct(hit1, len(rows)), "recall_at_3": pct(hit3, len(rows)),
                        "mrr": round(sum(rr) / len(rr), 3)}
    return out, failures


# ------------------------------------------------------------------ conversation turns
SCRIPTS = [
    ("bank_cheque", "ta", ["Lakshmi Traders", "25000", "இன்று", "1", "ஆம்"]),
    ("lpg_connection", "hi", ["1", "Ravi Kumar", "Mohan Kumar", "15/08/1990", "2", "9840012345", "skip",
                              "इसका मतलब क्या है?", "2345 6789 0124"]),
    ("bank_savings_account", "en", ["SBI, Anna Nagar", "my name is ravi kumar", "Mohan Kumar", "15 Aug 1990", "1",
                                    "married", "12345", "98400 12345", "skip", "change my mobile number",
                                    "9123456780"]),
]


def eval_turns() -> dict:
    from app.service import SessionManager

    sm = SessionManager()
    times, calls = [], []
    for form_id, lang, answers in SCRIPTS:
        sid = sm.start(form_id, lang)["session_id"]
        for text in answers:
            before = llm_module.STATS["calls"]
            t0 = time.perf_counter()
            sm.send(sid, text)
            times.append((time.perf_counter() - t0) * 1000)
            calls.append(llm_module.STATS["calls"] - before)
        sm.delete(sid)
    times.sort()
    return {"turns": len(times), "median_ms": round(statistics.median(times)),
            "p95_ms": round(times[max(0, int(len(times) * 0.95) - 1)]),
            "avg_llm_calls_per_turn": round(sum(calls) / len(calls), 2),
            "turns_with_no_llm_call": pct(sum(1 for c in calls if c == 0), len(calls))}


# ------------------------------------------------------------------ report
def run(mode: str) -> tuple[dict, list[dict]]:
    set_mode(mode)
    print(f"\n=== mode: {mode} ===", flush=True)
    t0 = time.time()
    res, fails = {}, []
    for name, fn in [("intent", eval_intent), ("extraction", eval_extraction), ("rag", eval_rag)]:
        print(f"  {name}...", flush=True)
        r, f = fn(load(name))
        res[name], fails = r, fails + f
    print("  conversation turns...", flush=True)
    res["turns"] = eval_turns()
    lat = sorted(llm_module.STATS["latencies_ms"])
    res["llm"] = {"calls": llm_module.STATS["calls"], "errors": llm_module.STATS["errors"],
                  "median_call_ms": round(statistics.median(lat)) if lat else None}
    res["seconds"] = round(time.time() - t0, 1)
    return res, fails


def markdown(results: dict, meta: dict) -> str:
    modes = list(results)
    col = lambda f: " | ".join(str(f(results[m])) for m in modes)  # noqa: E731
    head = "| Metric | " + " | ".join("Rules only" if m == "rules" else "Rules + Groq LLM" for m in modes) + " |"
    sep = "|---|" + "---|" * len(modes)
    r0 = results[modes[0]]
    lines = [
        "# Form Saathi evaluation results", "",
        f"Run on {meta['date']}. Chat model: `{meta['model']}`.", "",
        f"Test sets: {r0['intent']['n']} intent messages, {r0['extraction']['n']} extraction cases, "
        f"{r0['rag']['all_notes']['n']} RAG questions, {r0['turns']['turns']} scripted chat turns. "
        "Languages: English, Tamil, Hindi, Odia. The test sets were written by the project author, "
        "so treat these as a first measurement rather than a benchmark.", "",
        head, sep,
        f"| Intent accuracy | {col(lambda r: str(r['intent']['accuracy']) + '%')} |",
        f"| Extraction accuracy (overall) | {col(lambda r: str(r['extraction']['accuracy']) + '%')} |",
        f"| Valid inputs extracted correctly | {col(lambda r: str(r['extraction']['valid_inputs_extracted_correctly']) + '%')} |",
        f"| Invalid inputs rejected | {col(lambda r: str(r['extraction']['invalid_inputs_rejected']) + '%')} |",
        f"| RAG recall@3 (all notes) | {col(lambda r: str(r['rag']['all_notes']['recall_at_3']) + '%')} |",
        f"| RAG recall@3 (filtered by form, as in the app) | {col(lambda r: str(r['rag']['filtered_by_form']['recall_at_3']) + '%')} |",
        f"| RAG hit@1 (all notes) | {col(lambda r: str(r['rag']['all_notes']['hit_at_1']) + '%')} |",
        f"| Median time per chat turn | {col(lambda r: str(r['turns']['median_ms']) + ' ms')} |",
        f"| 95th percentile time per turn | {col(lambda r: str(r['turns']['p95_ms']) + ' ms')} |",
        f"| LLM calls per turn (average) | {col(lambda r: r['turns']['avg_llm_calls_per_turn'])} |",
        f"| Turns answered with no LLM call | {col(lambda r: str(r['turns']['turns_with_no_llm_call']) + '%')} |",
        "", "## Intent accuracy by language", "",
        "| Language | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes),
    ]
    for lang in r0["intent"]["by_language"]:
        lines.append(f"| {lang} (n={r0['intent']['by_language'][lang]['n']}) | "
                     + col(lambda r: str(r['intent']['by_language'][lang]['accuracy']) + '%') + " |")
    lines += ["", "## Intent recall by class", "", "| Class | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
    for cls in r0["intent"]["by_class"]:
        lines.append(f"| {cls} (n={r0['intent']['by_class'][cls]['n']}) | "
                     + col(lambda r: str(r['intent']['by_class'][cls]['recall']) + '%') + " |")
    lines += ["", "## Extraction accuracy by language", "", "| Language | " + " | ".join(modes) + " |",
              "|---|" + "---|" * len(modes)]
    for lang in r0["extraction"]["by_language"]:
        lines.append(f"| {lang} (n={r0['extraction']['by_language'][lang]['n']}) | "
                     + col(lambda r: str(r['extraction']['by_language'][lang]['accuracy']) + '%') + " |")
    lines += ["", "Every miss is listed in `failures_<mode>.jsonl` in this folder.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["rules", "llm", "both"], default="both")
    args = ap.parse_args()
    has_key = bool(get_settings().groq_api_key)
    modes = ["rules", "llm"] if args.mode == "both" else [args.mode]
    if "llm" in modes and not has_key:
        if args.mode == "llm":
            sys.exit("GROQ_API_KEY is not set (add it to backend/.env).")
        print("No GROQ_API_KEY found - running rules-only.")
        modes = ["rules"]

    RESULTS.mkdir(exist_ok=True)
    results = {}
    for mode in modes:
        res, fails = run(mode)
        results[mode] = res
        with open(RESULTS / f"failures_{mode}.jsonl", "w", encoding="utf-8") as f:
            for row in fails:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    # Report the model the client actually used: it may differ from the configured one when the key lacks access.
    model = llm_module.get_llm().chat_model if "llm" in modes else "none (rules only)"
    meta = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "model": model}
    (RESULTS / "eval_results.json").write_text(json.dumps({"meta": meta, "results": results}, indent=2), encoding="utf-8")
    md = markdown(results, meta)
    (RESULTS / "EVAL.md").write_text(md, encoding="utf-8")
    print("\n" + md)
    print(f"Saved to {RESULTS}")


if __name__ == "__main__":
    main()
