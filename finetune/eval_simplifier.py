"""Compare the base model and the fine-tuned simplifier on the held-out set.

    python eval_simplifier.py --finetuned http://localhost:8001/simplify --base http://localhost:8002/simplify

The Colab notebook imports evaluate() and runs the same comparison in-process, so you don't need
to serve the model to get the numbers.

Metrics (per language and overall):
  chrF       character n-gram F-score against the reference plain sentence (works for Indic scripts)
  jargon     % of outputs that still contain an English jargon word (lower is better)
  script     % of outputs actually written in the requested script (higher is better)
  words      average output length in words (shorter is usually plainer)
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import requests

from build_dataset import JARGON_WORDS, SCRIPT


def chrf(hyp: str, ref: str, n: int = 6, beta: float = 2.0) -> float:
    hyp, ref = re.sub(r"\s+", "", hyp), re.sub(r"\s+", "", ref)
    precisions, recalls = [], []
    for k in range(1, n + 1):
        h = Counter(hyp[i:i + k] for i in range(len(hyp) - k + 1))
        r = Counter(ref[i:i + k] for i in range(len(ref) - k + 1))
        if not h or not r:
            continue
        overlap = sum((h & r).values())
        precisions.append(overlap / sum(h.values()))
        recalls.append(overlap / sum(r.values()))
    if not precisions:
        return 0.0
    p, rc = sum(precisions) / len(precisions), sum(recalls) / len(recalls)
    return 0.0 if p + rc == 0 else 100 * (1 + beta ** 2) * p * rc / (beta ** 2 * p + rc)


def in_script(text: str, lang: str) -> bool:
    if lang not in SCRIPT:
        return bool(re.search(r"[A-Za-z]", text))
    letters = re.sub(r"[\s\d\W]", "", text)
    return bool(letters) and len(re.findall(SCRIPT[lang], text)) >= 0.5 * len(letters)


def evaluate(predict, rows: list[dict]) -> dict:
    """predict: a URL of a /simplify endpoint, or a function (list of (text, lang)) -> list of outputs."""
    if isinstance(predict, str):
        url = predict
        predict = lambda batch: [requests.post(url, json={"text": t, "lang": l}, timeout=120).json()["plain"]
                                 for t, l in batch]
    inputs = [(row["messages"][1]["content"].split("] ", 1)[1], row["lang"]) for row in rows]
    hyps = predict(inputs)
    agg = defaultdict(lambda: defaultdict(list))
    for row, hyp in zip(rows, hyps):
        lang, ref = row["lang"], row["messages"][2]["content"]
        for key in (lang, "all"):
            agg[key]["chrf"].append(chrf(hyp, ref))
            agg[key]["jargon"].append(100.0 * bool(set(re.findall(r"[a-z]+", hyp.lower())) & JARGON_WORDS))
            agg[key]["script"].append(100.0 * in_script(hyp, lang))
            agg[key]["words"].append(len(hyp.split()))
    return {k: {m: round(sum(v) / len(v), 1) for m, v in metrics.items()} for k, metrics in agg.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--finetuned", required=True)
    ap.add_argument("--base")
    ap.add_argument("--val", default=str(Path(__file__).parent / "data/val.jsonl"))
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(args.val, encoding="utf-8") if l.strip()]
    results = {"finetuned": evaluate(args.finetuned, rows)}
    if args.base:
        results["base"] = evaluate(args.base, rows)
    report(results)
    Path("eval_results.json").write_text(json.dumps(results, indent=2))


def report(results: dict) -> None:
    print(f"{'model':<10} {'lang':<5} {'chrF':>6} {'jargon%':>8} {'script%':>8} {'words':>6}")
    for name, res in results.items():
        for lang, m in sorted(res.items()):
            print(f"{name:<10} {lang:<5} {m['chrf']:>6} {m['jargon']:>8} {m['script']:>8} {m['words']:>6}")


if __name__ == "__main__":
    main()
