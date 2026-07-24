import re
import unicodedata
from dataclasses import dataclass

from app.rag.vector_store import SearchResult

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WORD = re.compile(r"[a-z0-9]+")
NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "with",
}
FOLLOW_UP_TERMS = {"it", "its", "that", "those", "they", "them", "this", "these"}
FOLLOW_UP_PREFIXES = (
    "and ",
    "also ",
    "how about ",
    "what about ",
)
STANDALONE_REQUEST_TERMS = {"overview", "recap", "summarize", "summary"}
SMALL_TALK_TERMS = {
    "goodbye",
    "hello",
    "hey",
    "hi",
    "okay",
    "ok",
    "thanks",
}
INSTRUCTION_PATTERN = re.compile(
    r"\b(ignore|disregard|override|system prompt|developer message|follow these instructions|"
    r"reveal the prompt|do not cite)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ConflictNotice:
    source_a: str
    source_b: str
    values_a: tuple[str, ...]
    values_b: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "source_a": self.source_a,
            "source_b": self.source_b,
            "values_a": list(self.values_a),
            "values_b": list(self.values_b),
        }


def preprocess_query(question: str, max_length: int = 10_000) -> str:
    normalized = unicodedata.normalize("NFKC", question)
    normalized = CONTROL_CHARACTERS.sub(" ", normalized)
    return " ".join(normalized.split())[:max_length].strip()


def query_variants(question: str) -> list[str]:
    normalized = preprocess_query(question)
    if not normalized:
        return []
    variants = [normalized]
    clauses = re.split(r"\s*(?:,?\s+and\s+|;\s*)", normalized, flags=re.IGNORECASE)
    for clause in clauses:
        clause = clause.strip(" ,;")
        if len(content_tokens(clause)) >= 2 and clause not in variants:
            variants.append(clause)
    return variants[:4]


def contextualize_query(question: str, previous_user_question: str | None) -> str:
    normalized = preprocess_query(question)
    if not previous_user_question:
        return normalized
    previous = preprocess_query(previous_user_question)
    tokens = content_tokens(normalized)
    previous_tokens = content_tokens(previous)
    if (
        not previous_tokens
        or previous_tokens <= SMALL_TALK_TERMS
        or tokens & STANDALONE_REQUEST_TERMS
    ):
        return normalized
    is_follow_up = bool(tokens & FOLLOW_UP_TERMS) or normalized.lower().startswith(
        FOLLOW_UP_PREFIXES
    )
    if is_follow_up:
        return f"{previous} {normalized}".strip()
    return normalized


def content_tokens(text: str, *, exclude_numbers: bool = False) -> set[str]:
    tokens = set(WORD.findall(text.lower()))
    tokens -= STOP_WORDS
    if exclude_numbers:
        tokens = {token for token in tokens if not token.isdigit() and token not in NUMBER_WORDS}
    return tokens


def token_overlap(left: str, right: str) -> float:
    left_tokens = content_tokens(left)
    right_tokens = content_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


def deduplicate_results(
    results: list[SearchResult], overlap_threshold: float = 0.72
) -> list[SearchResult]:
    unique: list[SearchResult] = []
    for result in sorted(results, key=lambda item: item.score, reverse=True):
        duplicate = any(
            result.metadata.get("document_id") == existing.metadata.get("document_id")
            and token_overlap(result.text, existing.text) >= overlap_threshold
            for existing in unique
        )
        if not duplicate:
            unique.append(result)
    return unique


def factual_values(text: str) -> set[str]:
    values = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", text.lower()))
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text, re.IGNORECASE):
            values.add(value)
    return values


def detect_conflicts(results: list[SearchResult]) -> list[ConflictNotice]:
    conflicts: list[ConflictNotice] = []
    for index, left in enumerate(results):
        left_values = factual_values(left.text)
        if not left_values:
            continue
        for right in results[index + 1 :]:
            if left.metadata.get("document_id") == right.metadata.get("document_id"):
                continue
            right_values = factual_values(right.text)
            if not right_values or left_values == right_values:
                continue
            shared = content_tokens(left.text, exclude_numbers=True) & content_tokens(
                right.text, exclude_numbers=True
            )
            smaller = min(
                len(content_tokens(left.text, exclude_numbers=True)),
                len(content_tokens(right.text, exclude_numbers=True)),
            )
            if smaller and len(shared) / smaller >= 0.30:
                conflicts.append(
                    ConflictNotice(
                        source_a=str(left.metadata.get("source_filename", "Unknown source")),
                        source_b=str(right.metadata.get("source_filename", "Unknown source")),
                        values_a=tuple(sorted(left_values)),
                        values_b=tuple(sorted(right_values)),
                    )
                )
    return conflicts


def has_instruction_like_text(text: str) -> bool:
    return bool(INSTRUCTION_PATTERN.search(text))


def sanitize_citation_markers(answer: str, citation_count: int) -> str:
    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        return match.group(0) if 1 <= index <= citation_count else "[unsupported citation]"

    return re.sub(r"\[Source\s+(\d+)\]", replace, answer, flags=re.IGNORECASE).strip()
