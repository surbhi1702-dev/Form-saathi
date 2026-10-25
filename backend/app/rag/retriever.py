"""RAG retriever over the department knowledge base (rag/knowledge/*.md).

Each markdown file is split into chunks at '## ' headings and indexed with BM25.
BM25 needs no model download and works well for short, keyword-heavy rules text.
`as_langchain_retriever()` exposes the same index as a LangChain BaseRetriever so it
can be dropped into any LangChain chain; swap in a vector store later if needed.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
_STOP = set("a an the of to and or in on for is are be by with as at it this that from you your can if not no".split())


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower()) if t not in _STOP and len(t) > 1]


@dataclass
class Chunk:
    tag: str
    title: str
    heading: str
    text: str
    source: str
    tokens: list[str] = field(default_factory=list, repr=False)


def _parse(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        meta = dict(line.split(":", 1) for line in front.strip().splitlines() if ":" in line)
        meta = {k.strip(): v.strip() for k, v in meta.items()}
    chunks = []
    for part in re.split(r"^## ", body, flags=re.MULTILINE):
        part = part.strip()
        if not part:
            continue
        heading, _, text = part.partition("\n")
        chunk = Chunk(meta.get("tag", path.stem), meta.get("title", path.stem), heading.strip(), text.strip(),
                      meta.get("source", ""))
        chunk.tokens = tokenize(f"{chunk.title} {chunk.heading} {chunk.text}")
        chunks.append(chunk)
    return chunks


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.avgdl = sum(len(c.tokens) for c in chunks) / max(1, len(chunks))
        df = Counter(t for c in chunks for t in set(c.tokens))
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self.tf = [Counter(c.tokens) for c in chunks]

    def search(self, query: str, k: int = 3, tags: list[str] | None = None) -> list[tuple[Chunk, float]]:
        q = tokenize(query)
        results = []
        for i, chunk in enumerate(self.chunks):
            if tags and chunk.tag not in tags:
                continue
            tf, dl = self.tf[i], len(chunk.tokens)
            score = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    score += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if score > 0:
                results.append((chunk, score))
        return sorted(results, key=lambda x: -x[1])[:k]


@lru_cache(maxsize=1)
def get_index() -> BM25Index:
    chunks = [c for p in sorted(KNOWLEDGE_DIR.glob("*.md")) for c in _parse(p)]
    return BM25Index(chunks)


def retrieve(query: str, tags: list[str] | None = None, k: int = 3) -> list[Chunk]:
    return [c for c, _ in get_index().search(query, k=k, tags=tags)]


def as_langchain_retriever(tags: list[str] | None = None, k: int = 3):
    """Wrap the BM25 index as a LangChain retriever (requires langchain-core)."""
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever

    class FormSaathiRetriever(BaseRetriever):
        def _get_relevant_documents(self, query: str, *, run_manager=None):  # noqa: ARG002
            return [Document(page_content=c.text, metadata={"tag": c.tag, "title": c.title, "heading": c.heading,
                                                            "source": c.source})
                    for c in retrieve(query, tags=tags, k=k)]

    return FormSaathiRetriever()
