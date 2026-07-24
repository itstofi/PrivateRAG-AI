from dataclasses import dataclass

from app.ingestion.loaders import ExtractedPage


@dataclass(frozen=True)
class TextChunk:
    text: str
    page_number: int | None
    section: str | None
    chunk_number: int


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap smaller than chunk_size")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        target_end = min(start + chunk_size, len(text))
        end = target_end
        if target_end < len(text):
            boundary = max(text.rfind("\n", start, target_end), text.rfind(" ", start, target_end))
            if boundary > start + chunk_size // 2:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_pages(pages: list[ExtractedPage], chunk_size: int, overlap: int) -> list[TextChunk]:
    output: list[TextChunk] = []
    sequence = 0
    for page in pages:
        for text in split_text(page.text, chunk_size, overlap):
            sequence += 1
            output.append(
                TextChunk(
                    text=text,
                    page_number=page.page_number,
                    section=page.section,
                    chunk_number=sequence,
                )
            )
    return output
