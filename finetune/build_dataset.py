"""Build the jargon -> plain-language dataset for the simplifier model.

    python build_dataset.py                 # seed pairs only (offline)
    python build_dataset.py --augment 400   # + ~400 official sentences rewritten by Groq into 4 languages

Sources of "official" sentences: every field explanation, question and submit note in the
16 form schemas, plus every sentence of the RAG knowledge base. Groq writes the formal/jargon
version and plain versions in English, Tamil, Hindi and Odia; filters below drop bad pairs.

Output (chat format, ready for the QLoRA notebook):
    data/train.jsonl, data/val.jsonl   - split by source sentence, so no leakage between them
IMPORTANT: have native speakers spot-check a sample of the generated Tamil/Hindi/Odia rows.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "backend"
sys.path.insert(0, str(BACKEND))

SYSTEM = ("You rewrite official Indian form language into short, plain sentences that a person with little "
          "schooling understands. Answer in the language given in brackets. Keep numbers and codes unchanged.")
SCRIPT = {"ta": r"[஀-௿]", "hi": r"[ऀ-ॿ]", "or": r"[଀-୿]"}
JARGON_WORDS = {"hereinafter", "aforesaid", "furnish", "particulars", "affix", "duly", "liable", "tally",
                "whereas", "thereof", "herein", "undersigned", "enclose", "pursuant"}
LANGS = ["en", "ta", "hi", "or"]


def official_sentences() -> list[str]:
    from app.forms import engine
    from app.rag.retriever import get_index

    out = set()
    for form in engine.all_forms().values():
        for f in form["fields"]:
            for text in (f.get("explain"), (f.get("question") or {}).get("en")):
                if text and len(text.split()) >= 5:
                    out.add(text.strip())
        if form.get("submit_note"):
            out.add(form["submit_note"])
    for chunk in get_index().chunks:
        for sent in re.split(r"(?<=[.!?])\s+", chunk.text):
            if len(sent.split()) >= 6:
                out.add(sent.strip())
    return sorted(out)


def groq_pairs(sentence: str, key: str, model: str) -> list[dict]:
    import requests

    prompt = (
        "Here is a sentence about an Indian form:\n" + sentence + "\n\n"
        "1. Write it the way an Indian government/bank form would (formal, jargon-heavy), as 'jargon'.\n"
        "2. Write a plain version for someone with little schooling, under 25 words, in each of: "
        "English (en), Tamil (ta), Hindi (hi), Odia (or). Use everyday spoken words, not Sanskritised/literary words.\n"
        'Return JSON only: {"jargon": "...", "plain": {"en": "...", "ta": "...", "hi": "...", "or": "..."}}'
    )
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.4, "messages": [{"role": "user", "content": prompt}]},
                      timeout=60)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", text, re.DOTALL)
    data = json.loads(m.group()) if m else {}
    jargon = str(data.get("jargon", "")).strip()
    return [{"lang": lang, "jargon": jargon, "plain": str(data.get("plain", {}).get(lang, "")).strip(), "source": sentence}
            for lang in LANGS]


def keep(row: dict) -> bool:
    j, p, lang = row["jargon"], row["plain"], row["lang"]
    if not j or not p or len(p.split()) > 40:
        return False
    if lang in SCRIPT and len(re.findall(SCRIPT[lang], p)) < 0.5 * len(re.sub(r"[\s\d\W]", "", p) or "x"):
        return False  # mostly not in the target script
    if lang == "en" and set(re.findall(r"[a-z]+", p.lower())) & JARGON_WORDS:
        return False  # the "plain" version still has jargon
    return True


def to_chat(row: dict) -> dict:
    return {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"[{row['lang']}] {row['jargon']}"},
                         {"role": "assistant", "content": row["plain"]}],
            "lang": row["lang"], "source": row.get("source", row["jargon"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--augment", type=int, default=0, help="number of official sentences to send to Groq")
    ap.add_argument("--model", default=os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile"))
    ap.add_argument("--val-fraction", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    random.seed(args.seed)

    rows = [json.loads(l) for l in (HERE / "data/seed_pairs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.augment:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            sys.exit("Set GROQ_API_KEY to augment.")
        sentences = official_sentences()
        random.shuffle(sentences)
        for i, s in enumerate(sentences[: args.augment], 1):
            try:
                rows += groq_pairs(s, key, args.model)
            except Exception as exc:  # rate limit / bad JSON - skip this sentence
                print(f"skip ({exc})")
                time.sleep(2)
            if i % 25 == 0:
                print(f"{i}/{args.augment} sentences")

    seen, clean = set(), []
    for r in rows:
        k = (r["lang"], r["jargon"].lower(), r["plain"].lower())
        if k not in seen and keep(r):
            seen.add(k)
            clean.append(r)

    sources = sorted({r.get("source", r["jargon"]) for r in clean})
    random.shuffle(sources)
    val_sources = set(sources[: max(1, int(len(sources) * args.val_fraction))])
    train = [to_chat(r) for r in clean if r.get("source", r["jargon"]) not in val_sources]
    val = [to_chat(r) for r in clean if r.get("source", r["jargon"]) in val_sources]
    for name, data in [("train", train), ("val", val)]:
        with open(HERE / f"data/{name}.jsonl", "w", encoding="utf-8") as f:
            for row in data:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    by_lang = {l: sum(1 for r in clean if r["lang"] == l) for l in LANGS}
    print(f"kept {len(clean)}/{len(rows)} pairs  train={len(train)} val={len(val)}  per language={by_lang}")


if __name__ == "__main__":
    main()
