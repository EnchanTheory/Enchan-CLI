"""Japanese-compatible lexical retrieval and Enchan candidate selection."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Callable


INDEX_VERSION = 2


def character_ngrams(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    grams: list[str] = []
    for size in (2, 3):
        grams.extend(normalized[index:index + size] for index in range(max(0, len(normalized) - size + 1)))
    return grams


def build_lexical_index(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    counters = [Counter(character_ngrams(chunk["text"])) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for counter in counters:
        document_frequency.update(counter.keys())

    document_count = len(chunks)
    idf = {
        gram: math.log((document_count + 1) / (frequency + 1)) + 1.0
        for gram, frequency in document_frequency.items()
    }
    postings: dict[str, list[list[float | int]]] = defaultdict(list)
    norms: list[float] = []
    for index, counter in enumerate(counters):
        squared = 0.0
        for gram, frequency in counter.items():
            weight = float(frequency) * idf[gram]
            postings[gram].append([index, weight])
            squared += weight * weight
        norms.append(math.sqrt(squared))
    return {
        "version": INDEX_VERSION,
        "document_count": document_count,
        "idf": idf,
        "norms": norms,
        "postings": dict(postings),
    }


def retrieve_candidates(
    query: str,
    chunks: list[dict[str, Any]],
    index: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    query_counter = Counter(character_ngrams(query))
    idf = index.get("idf", {})
    query_weights = {
        gram: float(frequency) * float(idf[gram])
        for gram, frequency in query_counter.items()
        if gram in idf
    }
    query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
    if query_norm == 0:
        return []

    scores: dict[int, float] = defaultdict(float)
    for gram, query_weight in query_weights.items():
        for document_index, document_weight in index.get("postings", {}).get(gram, []):
            scores[int(document_index)] += query_weight * float(document_weight)

    norms = index.get("norms", [])
    ranked = []
    for document_index, dot_product in scores.items():
        if document_index >= len(chunks) or document_index >= len(norms) or not norms[document_index]:
            continue
        score = dot_product / (query_norm * float(norms[document_index]))
        if score > 0:
            ranked.append((score, str(chunks[document_index].get("id", "")), document_index))
    ranked.sort(key=lambda item: (-item[0], item[1]))

    candidates = []
    for score, _, document_index in ranked[:max(1, limit)]:
        candidate = dict(chunks[document_index])
        candidate["score"] = score
        candidates.append(candidate)
    return candidates


def _tfidf_vector(text: str, idf: dict[str, float]) -> tuple[dict[str, float], float]:
    counter = Counter(character_ngrams(text))
    vector = {
        gram: float(frequency) * float(idf[gram])
        for gram, frequency in counter.items()
        if gram in idf
    }
    norm = math.sqrt(sum(weight * weight for weight in vector.values()))
    return vector, norm


def build_candidate_similarity_edges(
    candidates: list[dict[str, Any]],
    index: dict[str, Any],
    threshold: float = 0.4,
) -> list[tuple[int, int]]:
    idf = index.get("idf", {})
    vectors = [_tfidf_vector(item["text"], idf) for item in candidates]
    edges: list[tuple[int, int]] = []
    for left in range(len(vectors)):
        left_vector, left_norm = vectors[left]
        if left_norm == 0:
            continue
        for right in range(left + 1, len(vectors)):
            right_vector, right_norm = vectors[right]
            if right_norm == 0:
                continue
            small, large = (left_vector, right_vector) if len(left_vector) <= len(right_vector) else (right_vector, left_vector)
            dot = sum(weight * large.get(gram, 0.0) for gram, weight in small.items())
            similarity = dot / (left_norm * right_norm)
            if similarity > threshold:
                edges.append((left, right))
    return edges


def select_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    limit: int,
    index: dict[str, Any] | None = None,
    selector: Callable[..., list[int]] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if not candidates or limit <= 0:
        return [], "relevance_fallback"
    try:
        if selector is not None:
            indices = selector(query, [item["text"] for item in candidates], limit, preserve_order=False)
        else:
            from backend.rag.enchan_selector import select_rag_candidate_indices
            edges = build_candidate_similarity_edges(candidates, index or {})
            indices = select_rag_candidate_indices(
                edges,
                [float(item.get("score", 0.0)) for item in candidates],
                limit,
                seed=42,
            )
        valid: list[int] = []
        seen = set()
        for value in indices:
            candidate_index = int(value)
            if 0 <= candidate_index < len(candidates) and candidate_index not in seen:
                valid.append(candidate_index)
                seen.add(candidate_index)
        if not valid:
            raise RuntimeError("Enchan selection returned no candidates")
        return [candidates[candidate_index] for candidate_index in valid[:limit]], "enchan_cosmic_v2"
    except Exception:
        return candidates[:limit], "relevance_fallback"

