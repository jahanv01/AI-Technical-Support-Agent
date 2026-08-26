"""Local BM25 retrieval over the knowledge-base/ Markdown corpus.

No embedding API call needed — keeps Task 1 fast, free, and deterministic.
Chunking strategy per DATA_SCHEMA.md: split each doc on '---' horizontal
rules, and keep the nearest heading as chunk metadata for traceability
(so matched_kb_doc can point back to a specific doc + section).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config import KB_DIR


@dataclass
class KBChunk:
    doc_path: str  # relative path, e.g. "products/databridge-pro.md"
    heading: str
    text: str


def load_kb_chunks(kb_dir: Path = KB_DIR) -> list[KBChunk]:
    """Walk kb_dir, split each .md file on '---', and return one KBChunk per section.

    TODO(you): implement. Track the most recent Markdown heading (#, ##, ###)
    seen before each '---' boundary so KBChunk.heading is populated.
    """
    raise NotImplementedError


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


class KBIndex:
    """BM25 index over KBChunk.text, built once and reused across calls."""

    def __init__(self, chunks: list[KBChunk]):
        self.chunks = chunks
        self._bm25 = BM25Okapi([_tokenize(c.text) for c in chunks]) if chunks else None

    @classmethod
    def build(cls, kb_dir: Path = KB_DIR) -> "KBIndex":
        return cls(load_kb_chunks(kb_dir))

    def search(self, query: str, top_k: int = 3) -> list[tuple[KBChunk, float]]:
        """Return up to top_k (chunk, score) pairs, highest score first.

        Callers should only treat a match as authoritative if the top score
        clears config.KB_MATCH_SCORE_THRESHOLD — otherwise leave
        matched_kb_doc unset rather than risk a hallucinated citation.
        """
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self.chunks, scores), key=lambda pair: pair[1], reverse=True)
        return ranked[:top_k]
