"""Text chunking utilities.

A small, dependency-free sliding-window chunker. It splits on paragraph/
sentence boundaries where possible so chunks stay semantically coherent,
while guaranteeing a hard upper bound on chunk size and a configurable
overlap between consecutive chunks to preserve context across boundaries.
"""
import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _split_into_sentences(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    sentences: list[str] = []
    for paragraph in paragraphs:
        sentences.extend(s for s in _SENTENCE_BOUNDARY.split(paragraph) if s)
    return sentences or [text.strip()] if text.strip() else []


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[str]:
    """Greedily pack sentences into chunks up to ``chunk_size`` characters.

    ``chunk_overlap`` characters from the tail of one chunk are carried into
    the start of the next so retrieval doesn't lose context that straddles a
    chunk boundary.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")

    sentences = _split_into_sentences(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = current[-chunk_overlap:] + " " + sentence if chunk_overlap else sentence
        else:
            # a single sentence longer than chunk_size: hard-split it
            for i in range(0, len(sentence), chunk_size - chunk_overlap):
                chunks.append(sentence[i : i + chunk_size])
            current = ""

    if current:
        chunks.append(current)

    return [c.strip() for c in chunks if c.strip()]
