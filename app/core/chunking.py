"""Document chunking for precise citations and hybrid search."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Chunking parameters
CHUNK_SIZE = 800  # characters (~256 tokens)
CHUNK_OVERLAP = 160  # 20% overlap
MIN_CHUNK_SIZE = 100  # minimum chunk size


@dataclass
class Chunk:
    """A document chunk with position information."""

    index: int
    text: str
    char_start: int
    char_end: int
    token_count: int | None = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.index,
            "chunk_text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "token_count": self.token_count,
        }


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English/German.

    This is a simple heuristic. For exact counts, use tiktoken.
    """
    return len(text) // 4


def split_into_sentences(text: str) -> list[tuple[str, int, int]]:
    """Split text into sentences with position tracking.

    Returns list of (sentence, start, end) tuples.
    """
    # Pattern for sentence boundaries (handles German and English)
    # Matches: . ! ? followed by space and uppercase, or end of string
    pattern = r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])|(?<=[.!?])$"

    sentences = []
    last_end = 0

    for match in re.finditer(pattern, text):
        sentence = text[last_end : match.start() + 1].strip()
        if sentence:
            sentences.append((sentence, last_end, match.start() + 1))
        last_end = match.end()

    # Add remaining text as last sentence
    if last_end < len(text):
        remaining = text[last_end:].strip()
        if remaining:
            sentences.append((remaining, last_end, len(text)))

    return sentences


def split_into_paragraphs(text: str) -> list[tuple[str, int, int]]:
    """Split text into paragraphs with position tracking.

    Paragraphs are separated by blank lines (2+ newlines).
    Returns list of (paragraph, start, end) tuples.
    """
    paragraphs = []
    # Split on multiple newlines
    pattern = r"\n\s*\n+"

    last_end = 0
    for match in re.finditer(pattern, text):
        para = text[last_end : match.start()].strip()
        if para:
            paragraphs.append((para, last_end, match.start()))
        last_end = match.end()

    # Add remaining text as last paragraph
    if last_end < len(text):
        remaining = text[last_end:].strip()
        if remaining:
            paragraphs.append((remaining, last_end, len(text)))

    return paragraphs


def chunk_document(
    fulltext: str,
    title: str = "",
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    min_chunk_size: int = MIN_CHUNK_SIZE,
) -> list[Chunk]:
    """Chunk a document into overlapping segments for embedding.

    Uses recursive strategy:
    1. First try to split by paragraphs
    2. If paragraphs are too long, split by sentences
    3. If sentences are too long, split by characters

    Each chunk includes overlap with neighbors to preserve context
    at boundaries.

    Args:
        fulltext: The document text to chunk
        title: Optional document title (prepended to first chunk)
        chunk_size: Target chunk size in characters (~256 tokens at 800 chars)
        chunk_overlap: Overlap between chunks in characters
        min_chunk_size: Minimum chunk size (avoid tiny chunks)

    Returns:
        List of Chunk objects with position data for citations
    """
    if not fulltext or not fulltext.strip():
        return []

    # Clean the text
    text = fulltext.strip()

    # Prepend title to text if provided
    if title:
        text = f"{title}\n\n{text}"

    chunks = []
    current_chunk_text = ""
    current_start = 0
    chunk_index = 0

    # First split into paragraphs
    paragraphs = split_into_paragraphs(text)

    for para_text, para_start, para_end in paragraphs:
        # If paragraph fits in current chunk, add it
        if len(current_chunk_text) + len(para_text) + 2 <= chunk_size:
            if current_chunk_text:
                current_chunk_text += "\n\n" + para_text
            else:
                current_chunk_text = para_text
                current_start = para_start
            continue

        # Paragraph doesn't fit - finalize current chunk if it exists
        if current_chunk_text and len(current_chunk_text) >= min_chunk_size:
            chunks.append(
                Chunk(
                    index=chunk_index,
                    text=current_chunk_text,
                    char_start=current_start,
                    char_end=current_start + len(current_chunk_text),
                    token_count=estimate_tokens(current_chunk_text),
                )
            )
            chunk_index += 1

            # Start new chunk with overlap from previous
            overlap_text = current_chunk_text[-chunk_overlap:] if chunk_overlap > 0 else ""
            current_chunk_text = overlap_text
            current_start = para_start - len(overlap_text) if overlap_text else para_start

        # If paragraph itself is too long, split it
        if len(para_text) > chunk_size:
            # Split by sentences
            sentences = split_into_sentences(para_text)

            for sent_text, sent_rel_start, sent_rel_end in sentences:
                abs_start = para_start + sent_rel_start
                abs_end = para_start + sent_rel_end

                if len(current_chunk_text) + len(sent_text) + 1 <= chunk_size:
                    if current_chunk_text:
                        current_chunk_text += " " + sent_text
                    else:
                        current_chunk_text = sent_text
                        current_start = abs_start
                else:
                    # Save current chunk
                    if current_chunk_text and len(current_chunk_text) >= min_chunk_size:
                        chunks.append(
                            Chunk(
                                index=chunk_index,
                                text=current_chunk_text,
                                char_start=current_start,
                                char_end=current_start + len(current_chunk_text),
                                token_count=estimate_tokens(current_chunk_text),
                            )
                        )
                        chunk_index += 1

                    # Start new with overlap
                    overlap_text = current_chunk_text[-chunk_overlap:] if chunk_overlap > 0 else ""
                    current_chunk_text = (overlap_text + " " + sent_text).strip() if overlap_text else sent_text
                    current_start = abs_start - len(overlap_text) if overlap_text else abs_start
        else:
            # Paragraph fits on its own
            if current_chunk_text:
                current_chunk_text += "\n\n" + para_text
            else:
                current_chunk_text = para_text
                current_start = para_start

    # Don't forget the last chunk
    if current_chunk_text and len(current_chunk_text) >= min_chunk_size:
        chunks.append(
            Chunk(
                index=chunk_index,
                text=current_chunk_text,
                char_start=current_start,
                char_end=current_start + len(current_chunk_text),
                token_count=estimate_tokens(current_chunk_text),
            )
        )

    return chunks


def chunk_for_embedding(
    text: str, title: str = "", max_tokens: int = 8000
) -> str:
    """Prepare text for single-document embedding.

    If text is short enough, return as-is with title prepended.
    If too long, truncate intelligently.

    Args:
        text: Document text
        title: Optional title to prepend
        max_tokens: Maximum tokens (default 8000 for OpenAI models)

    Returns:
        Text prepared for embedding
    """
    max_chars = max_tokens * 4  # rough estimate

    if title:
        text = f"{title}\n\n{text}"

    if len(text) <= max_chars:
        return text

    # Truncate at sentence boundary if possible
    truncated = text[:max_chars]
    last_period = truncated.rfind(". ")
    if last_period > max_chars * 0.8:  # at least 80% of content
        return truncated[: last_period + 1]

    return truncated


def get_chunking_info() -> dict:
    """Get information about chunking parameters for admin UI."""
    return {
        "chunk_size": CHUNK_SIZE,
        "chunk_size_tokens": estimate_tokens("x" * CHUNK_SIZE),
        "chunk_overlap": CHUNK_OVERLAP,
        "chunk_overlap_percent": round(CHUNK_OVERLAP / CHUNK_SIZE * 100),
        "min_chunk_size": MIN_CHUNK_SIZE,
        "description": (
            f"Dokumente werden in Abschnitte von ~{CHUNK_SIZE} Zeichen "
            f"(~{estimate_tokens('x' * CHUNK_SIZE)} Tokens) aufgeteilt. "
            f"{round(CHUNK_OVERLAP / CHUNK_SIZE * 100)}% Ueberlappung verhindert "
            "Kontextverlust an Grenzen."
        ),
    }
