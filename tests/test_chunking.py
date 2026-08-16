import pytest

from app.services.chunking import chunk_text


def test_short_text_returns_single_chunk():
    text = "This is a short sentence. It fits in one chunk."
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=20)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_splits_into_multiple_chunks():
    sentence = "The quick brown fox jumps over the lazy dog. "
    text = sentence * 40  # ~1880 chars
    chunks = chunk_text(text, chunk_size=300, chunk_overlap=50)

    assert len(chunks) > 1
    assert all(len(c) <= 300 + 50 for c in chunks)  # allow small overlap slack


def test_overlap_carries_context_between_chunks():
    sentence = "Sentence number %d provides unique context. "
    text = "".join(sentence % i for i in range(30))
    chunks = chunk_text(text, chunk_size=250, chunk_overlap=60)

    assert len(chunks) > 1
    # the tail of chunk N should share some characters with the head of chunk N+1
    tail = chunks[0][-60:].split(" ", 1)[-1][:10]
    assert chunks[0][-30:] in chunks[1] or chunks[1].startswith(tail)


def test_empty_text_returns_no_chunks():
    assert chunk_text("", chunk_size=100, chunk_overlap=10) == []


def test_invalid_chunk_size_raises():
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_size=0, chunk_overlap=0)


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_size=100, chunk_overlap=100)
