# Form Saathi evaluation results

Run on 2026-10-25 11:04. Chat model: `openai/gpt-oss-120b`.

Test sets: 92 intent messages, 72 extraction cases, 43 RAG questions, 25 scripted chat turns. Languages: English, Tamil, Hindi, Odia. The test sets were written by the project author, so treat these as a first measurement rather than a benchmark.

| Metric | Rules only | Rules + Groq LLM |
|---|---|---|
| Intent accuracy | 85.9% | 96.7% |
| Extraction accuracy (overall) | 80.6% | 93.1% |
| Valid inputs extracted correctly | 77.4% | 93.5% |
| Invalid inputs rejected | 100.0% | 90.0% |
| RAG recall@3 (all notes) | 95.3% | 95.3% |
| RAG recall@3 (filtered by form, as in the app) | 100.0% | 100.0% |
| RAG hit@1 (all notes) | 86.0% | 86.0% |
| Median time per chat turn | 4 ms | 1585 ms |
| 95th percentile time per turn | 5 ms | 5926 ms |
| LLM calls per turn (average) | 0.0 | 1.04 |
| Turns answered with no LLM call | 100.0% | 40.0% |

## Intent accuracy by language

| Language | rules | llm |
|---|---|---|
| en (n=54) | 83.3% | 94.4% |
| hi (n=15) | 80.0% | 100.0% |
| or (n=9) | 100.0% | 100.0% |
| ta (n=14) | 92.9% | 100.0% |

## Intent recall by class

| Class | rules | llm |
|---|---|---|
| answer (n=34) | 100.0% | 100.0% |
| correct (n=16) | 87.5% | 100.0% |
| explain (n=26) | 84.6% | 88.5% |
| skip (n=16) | 56.2% | 100.0% |

## Extraction accuracy by language

| Language | rules | llm |
|---|---|---|
| en (n=56) | 85.7% | 94.6% |
| hi (n=5) | 60.0% | 80.0% |
| or (n=3) | 66.7% | 100.0% |
| ta (n=8) | 62.5% | 87.5% |

Every miss is listed in `failures_<mode>.jsonl` in this folder.
