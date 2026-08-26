"""Local BM25 retrieval over the knowledge-base/ Markdown corpus.

No embedding API call needed — keeps Task 1 fast, free, and deterministic.

Chunking: split on '###' headings rather than the '---' section rules alone
(DATA_SCHEMA.md's suggestion). In practice a single '---'-delimited section
(e.g. "Core Modules") bundles several unrelated '###' subsections (Data
Ingestion, Schema Management, Connectors, API...), each with its own error
codes — splitting only on '---' would make retrieval too coarse to
distinguish "ERR_CONNECTION_TIMEOUT" from an OAuth token-refresh question.
'#'/'##' ancestors are kept as a breadcrumb in KBChunk.heading for traceability.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config import KB_DIR

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


@dataclass
class KBChunk:
    doc_path: str  # relative path, e.g. "products/databridge-pro.md"
    heading: str  # breadcrumb, e.g. "DataBridge Pro — Product Reference > Core Modules > Data Ingestion"
    text: str


def _parse_file(path: Path, rel_path: str) -> list[KBChunk]:
    lines = path.read_text(encoding="utf-8").splitlines()

    chunks: list[KBChunk] = []
    ancestors = ["", ""]  # current h1, h2
    current_heading_line = ""
    current_breadcrumb = rel_path
    buffer: list[str] = []

    def flush():
        text = "\n".join(buffer).strip()
        if text:
            chunks.append(KBChunk(doc_path=rel_path, heading=current_breadcrumb, text=f"{current_heading_line}\n{text}".strip()))
        buffer.clear()

    for line in lines:
        if line.strip() == "---":
            continue  # section rule is a no-op for chunk boundaries here; '###' drives them
        match = _HEADING_RE.match(line)
        if match:
            flush()
            level, title = len(match.group(1)), match.group(2).strip()
            if level == 1:
                ancestors[0] = title
                ancestors[1] = ""
            elif level == 2:
                ancestors[1] = title
            current_heading_line = line
            crumbs = [c for c in ancestors[: level - 1] + [title] if c]
            current_breadcrumb = " > ".join(crumbs) if crumbs else rel_path
        else:
            buffer.append(line)
    flush()
    return chunks


def load_kb_chunks(kb_dir: Path = KB_DIR) -> list[KBChunk]:
    chunks: list[KBChunk] = []
    for path in sorted(kb_dir.rglob("*.md")):
        rel_path = str(path.relative_to(kb_dir)).replace("\\", "/")
        chunks.extend(_parse_file(path, rel_path))
    return chunks


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


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
