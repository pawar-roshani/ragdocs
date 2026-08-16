"""Answer generation.

Uses OpenAI when ``OPENAI_API_KEY`` is configured for a fluent, synthesized
answer. Otherwise falls back to a deterministic extractive strategy that
stitches together the most relevant retrieved sentences, so the full
pipeline runs end to end with zero external dependencies or cost.
"""
from app.core.config import get_settings
from app.services.retrieval import RetrievedChunk

settings = get_settings()

_SYSTEM_PROMPT = (
    "You are a precise assistant that answers questions using ONLY the "
    "provided context. If the answer isn't in the context, say you don't "
    "know rather than guessing. Cite sources inline as [1], [2], etc. "
    "matching the order the context snippets are given in."
)


def _build_context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[{i + 1}] (from {c.filename}) {c.chunk.content}" for i, c in enumerate(chunks)
    )


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> tuple[str, str]:
    """Returns ``(answer, mode)`` where mode is 'openai' or 'extractive'."""
    if not chunks:
        return (
            "I couldn't find anything relevant in the ingested documents to answer that.",
            "extractive",
        )

    if settings.is_generation_enabled:
        return _generate_with_openai(question, chunks), "openai"
    return _generate_extractive(chunks), "extractive"


def _generate_with_openai(question: str, chunks: list[RetrievedChunk]) -> str:
    from openai import OpenAI  # imported lazily so it's an optional dependency at runtime

    client = OpenAI(api_key=settings.openai_api_key)
    context = _build_context(chunks)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def _generate_extractive(chunks: list[RetrievedChunk]) -> str:
    lines = [
        f"Based on the most relevant passages found ({len(chunks)} match(es)):",
        "",
    ]
    for i, c in enumerate(chunks):
        snippet = c.chunk.content.strip()
        if len(snippet) > 400:
            snippet = snippet[:400].rsplit(" ", 1)[0] + "..."
        lines.append(f"[{i + 1}] ({c.filename}, similarity={c.similarity:.2f}) {snippet}")
    lines.append("")
    lines.append(
        "Set OPENAI_API_KEY to have these passages synthesized into a "
        "single natural-language answer instead of shown verbatim."
    )
    return "\n".join(lines)
