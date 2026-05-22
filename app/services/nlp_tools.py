import re
from collections import Counter
from typing import Any


CODE_ENTITY_PATTERNS = {
    "pandas_api": re.compile(
        r"\b(?:pd|pandas)\.[A-Za-z_][A-Za-z0-9_]*|\b(?:DataFrame|Series|Index|GroupBy)\b"
    ),
    "method_or_attribute": re.compile(
        r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b"
    ),
    "function_call": re.compile(
        r"\b[A-Za-z_][A-Za-z0-9_]*\("
    ),
    "exception": re.compile(
        r"\b[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Warning)\b"
    ),
    "version": re.compile(
        r"\b\d+\.\d+(?:\.\d+)?\b"
    ),
    "file_path": re.compile(
        r"(?:[A-Za-z]:\\[^\s]+|(?:\.{1,2}/)?[A-Za-z0-9_\-/]+\.py)"
    ),
    "github_issue": re.compile(
        r"#\d+|https://github\.com/[^\s)]+"
    ),
}


STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on", "is",
    "are", "was", "were", "this", "that", "it", "as", "by", "from", "be", "can",
    "not", "but", "we", "you", "i", "they", "if", "then", "when", "using", "use",
}


def extract_entities(text: str) -> dict[str, Any]:
    """
    CPU-only NER-style extractor for code-shaped entities.

    This is not a statistical NER model. It is a deterministic extractor designed
    for GitHub issues and maintainer text, where API names, exceptions, versions,
    and issue references are more useful than person/place names.
    """
    entities: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for entity_type, pattern in CODE_ENTITY_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(0).strip()

            if entity_type == "function_call":
                value = value.rstrip("(")

            key = (entity_type, value)

            if key in seen:
                continue

            seen.add(key)
            entities.append(
                {
                    "type": entity_type,
                    "value": value,
                }
            )

    return {
        "entity_count": len(entities),
        "entities": entities,
    }


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def tokenize_words(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)
        if token.lower() not in STOPWORDS and len(token) > 2
    ]


def summarize_text(text: str, max_sentences: int = 3) -> dict[str, Any]:
    """
    CPU-only extractive summarizer.

    It scores sentences by important word frequency and returns the highest
    scoring sentences in original order.
    """
    sentences = split_sentences(text)

    if not sentences:
        return {
            "summary": "",
            "sentence_count": 0,
            "strategy": "extractive_frequency",
        }

    if len(sentences) <= max_sentences:
        return {
            "summary": " ".join(sentences),
            "sentence_count": len(sentences),
            "strategy": "extractive_frequency",
        }

    word_counts = Counter(tokenize_words(text))

    scored: list[tuple[int, float, str]] = []

    for index, sentence in enumerate(sentences):
        words = tokenize_words(sentence)

        if not words:
            score = 0.0
        else:
            score = sum(word_counts[word] for word in words) / len(words)

        # Small bonus for sentences with code/API-looking terms.
        if re.search(r"\b(?:DataFrame|Series|GroupBy|read_csv|groupby|dtype|numeric_only)\b", sentence):
            score += 1.0

        scored.append((index, score, sentence))

    selected = sorted(scored, key=lambda item: item[1], reverse=True)[:max_sentences]
    selected_in_original_order = sorted(selected, key=lambda item: item[0])

    summary = " ".join(sentence for _, _, sentence in selected_in_original_order)

    return {
        "summary": summary,
        "sentence_count": len(sentences),
        "selected_sentence_count": len(selected_in_original_order),
        "strategy": "extractive_frequency",
    }   